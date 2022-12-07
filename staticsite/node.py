from __future__ import annotations

import contextlib
import logging
import os
import re
from typing import TYPE_CHECKING, Any, Generator, Optional, Sequence, TextIO, Type, Union

from . import metadata
from .metadata import SiteElement

if TYPE_CHECKING:
    from . import file
    from .asset import Asset
    from .page import Page
    from .site import Site

log = logging.getLogger("structure")


re_pathsep = re.compile(re.escape(os.sep) + "+")


class SkipPage(Exception):
    """
    Exception raised when a page should not be added to the site
    """
    pass


class Path(tuple[str]):
    """
    Path in the site, split into components
    """
    @property
    def head(self) -> str:
        """
        Return the first element in the path
        """
        return self[0]

    @property
    def tail(self) -> Path:
        """
        Return the Path after the first element
        """
        # TODO: check if it's worth making this a cached_property
        return Path(self[1:])

    @classmethod
    def from_string(cls, path: str) -> "Path":
        """
        Split a string into a path
        """
        return cls(re_pathsep.split(path.strip(os.sep)))


class Node(SiteElement):
    """
    One node in the rendered directory hierarchy of the site
    """
    site_path = metadata.Metadata("site_path", doc="""
        Where a content directory appears in the site.

        By default, is is the `site_path` of the parent directory, plus the directory
        name.

        If you are publishing the site at `/prefix` instead of the root of the domain,
        override this with `/prefix` in the content root.
    """)

    def __init__(
            self,
            site: Site,
            name: str, *,
            parent: Optional[Node] = None):
        super().__init__(site, parent=parent)
        # Basename of this directory
        self.name: str = name
        # Parent node, or None if this is the root
        self.parent: Optional[Node] = parent
        # Index page for this directory, if present
        self.page: Optional[Page] = None
        # Pages to be rendered at this location
        self.build_pages: dict[str, Page] = {}
        # Subdirectories
        self.sub: dict[str, Node] = {}

    def print(self, lead: str = "", file: Optional[TextIO] = None):
        if self.page:
            print(f"{lead}{self.name!r} home: {self.page!r}", file=file)
        else:
            print(f"{lead}{self.name!r} (no home)", file=file)
        for name, page in self.build_pages.items():
            print(f"{lead}- {name} → {page!r}", file=file)
        for name, node in self.sub.items():
            node.print(lead + "+ ", file=file)

    def iter_pages(self, prune: Sequence[Node] = ()) -> Generator[Page, None, None]:
        """
        Iterate all pages in this subtree
        """
        # Avoid nodes in prune
        if self in prune:
            return
        yield from self.build_pages.values()
        for node in self.sub.values():
            yield from node.iter_pages(prune)

    def lookup(self, path: Path) -> Optional[Node]:
        """
        Return the subnode at the given relative path, or None if it does not
        exist.

        Path elements of "." and ".." are supported
        """
        if not path:
            return self
        if path.head == ".":
            # Probably not worth trying to avoid a recursion step here, since
            # this should not be a common occurrence
            return self.lookup(path.tail)
        elif path.head == "..":
            if self.parent is None:
                return None
            else:
                return self.parent.lookup(path.tail)
        elif (sub := self.sub.get(path.head)):
            return sub.lookup(path.tail)
        return None

    def resolve_path(self, target: Union[str, "Page"], static=False) -> "Page":
        """
        Return a Page from the site, given a source or site path relative to
        this page.

        The path is resolved relative to this node, and if not found, relative
        to the parent node, and so on until the top.
        """
        from .page import Page
        if isinstance(target, Page):
            return target
        if target.startswith("/"):
            root = self.site.structure.root
            if static:
                root = root.lookup(Path.from_string(self.site.settings.STATIC_PATH))
            return root.lookup_page(Path.from_string(target))
        else:
            return self.lookup_page(Path.from_string(target))

    def lookup_page(self, path: Path) -> Optional[Page]:
        """
        Find a page by following path from this node

        The final path component can match:
        * a node name
        * the basename of a page's src_relpath
        * the rendered file name
        """
        # print(f"Node.lookup_page: {self.name=!r}, {self.page=!r}, {path=!r},"
        #       f" sub={self.sub.keys() if self.sub else 'None'}")

        if not path:
            return self.page

        if path.head == "..":
            return self.parent.lookup_page(path.tail)
        elif path.head in (".", ""):
            # Probably not worth trying to avoid a recursion step here, since
            # this should not be a common occurrence
            return self.lookup_page(path.tail)

        if len(path) > 1:
            if not self.sub:
                return None
            elif (subnode := self.sub.get(path.head)):
                # print(f"Node.lookup_page:  descend into {subnode.name!r} with {path.tail=!r}")
                return subnode.lookup_page(path.tail)
            else:
                return None

        # Match subnode name
        if self.sub and (subnode := self.sub.get(path.head)) and subnode.page:
            return subnode.page

        # Match subpage names and basename of src.relpath in subpages
        for name, page in self.build_pages.items():
            # print(f"Node.lookup_page:  build_pages[{name!r}] = {page!r} {page.src=!r}")
            if name == path.head:
                return page
            if page.src and path.head == os.path.basename(page.src.relpath):
                return page

        # Match basename of src.relpath in subpages
        for subnode in self.sub.values():
            if (page := subnode.page) and (src := page.src) and os.path.basename(src.relpath) == path.head:
                return page

        return None

    def compute_path(self) -> str:
        """
        Compute the build path for this node
        """
        if self.parent is None:
            return self.name
        else:
            return os.path.join(self.parent.compute_path(), self.name)

    def create_page(self, path: Optional[Path] = None, dst: Optional[str] = None, directory_index: bool = False, **kw):
        """
        Create a page of the given type, attaching it at the given path
        """
        if "meta" in kw:
            raise RuntimeError("do not pass meta to create_page")

        if directory_index and dst:
            raise RuntimeError(f"directory_index is True for a page with dst set ({dst=!r})")

        if dst is None and not directory_index and not path:
            raise RuntimeError(f"{self.compute_path()}: empty path for {kw['page_cls']}")

        # TODO: move site.is_page_ignored here?
        try:
            if dst:
                return self._create_leaf_page(dst=dst, path=path, **kw)
            else:
                return self._create_index_page(path=path, directory_index=directory_index, **kw)
        except SkipPage:
            return None

    def _create_index_page(
            self, *,
            page_cls: Type[Page],
            src: Optional[file.File] = None,
            path: Optional[Path] = None,
            directory_index: bool = False,
            meta_values: Optional[dict[str, Any]] = None,
            created_from: Optional[Page] = None,
            **kw):
        if path:
            # If a subpath is requested, delegate to subnodes
            with self.tentative_child(path.head) as node:
                return node._create_index_page(
                        page_cls=page_cls, src=src, path=path.tail,
                        meta_values=meta_values, created_from=created_from,
                        **kw)

        if directory_index:
            search_root_node = self
        else:
            search_root_node = self.parent

        # Create the page
        page = self.site.features.get_page_class(page_cls)(
            site=self.site, src=src, dst="index.html", node=self,
            search_root_node=search_root_node,
            created_from=created_from,
            leaf=False,
            directory_index=directory_index, meta_values=meta_values, **kw)
        if self.site.is_page_ignored(page):
            raise SkipPage()

        if self.page is not None:
            if self.page.TYPE == "asset" and page.TYPE == "asset":
                # First one wins, to allow overriding of assets in theme
                pass
            else:
                log.warn("%s: page %r replaces page %r", self.compute_path(), page, self.page)

        self.page = page
        self.site.structure.index(page)
        # if page.directory_index is False:
        #     print(f"{page=!r} dst is not set but page is not a directory index")

        self.build_pages["index.html"] = page
        return page

    def _create_leaf_page(
            self, *,
            page_cls: Type[Page],
            src: Optional[file.File] = None,
            dst: str,
            path: Optional[Path] = None,
            meta_values: Optional[dict[str, Any]] = None,
            created_from: Optional[Page] = None,
            **kw):
        if path:
            # If a subpath is requested, delegate to subnodes
            with self.tentative_child(path.head) as node:
                return node._create_leaf_page(
                        page_cls=page_cls, src=src, dst=dst, path=path.tail,
                        meta_values=meta_values, created_from=created_from,
                        **kw)

        # Create the page
        page = self.site.features.get_page_class(page_cls)(
            site=self.site, src=src, dst=dst,
            # TODO: switch to just self once we get rid of structure.pages:
            # this is only needed to get a good site_path there
            node=self,
            created_from=created_from,
            search_root_node=self,
            leaf=True,
            directory_index=False, meta_values=meta_values, **kw)
        if self.site.is_page_ignored(page):
            raise SkipPage()

        if (old := self.build_pages.get(dst)):
            if old.TYPE == "asset" and page.TYPE == "asset":
                # First one wins, to allow overriding of assets in theme
                pass
            else:
                log.warn("%s: page %r replaces page %r", self.compute_path(), page, old)

        self.build_pages[dst] = page
        self.site.structure.index(page)
        return page

    def add_asset(self, *, src: file.File, name: str) -> Asset:
        """
        Add an Asset as a subnode of this one
        """
        # Import here to avoid cyclical imports
        from .asset import Asset
        return self.create_page(page_cls=Asset, src=src, name=name, dst=name)

    def add_directory_index(self, src: file.File):
        """
        Add a directory index to this node
        """
        from . import dirindex
        return self.create_page(
            page_cls=dirindex.Dir,
            name=self.name,
            directory_index=True,
            src=src)

    @contextlib.contextmanager
    def tentative_child(self, name: str) -> Generator[Node, None, None]:
        """
        Add a child, removing it if an exception is raised
        """
        if (node := self.sub.get(name)):
            yield node
            return

        try:
            node = self.__class__(site=self.site, name=name, parent=self)
            self.sub[name] = node
            yield node
        except Exception:
            # Rollback the addition
            self.sub.pop(name, None)

    def child(self, name: str) -> Node:
        """
        Return the given subnode, creating it if missing
        """
        if (node := self.sub.get(name)):
            return node

        node = self.__class__(site=self.site, name=name, parent=self)
        self.sub[name] = node
        return node

    def at_path(self, path: Path) -> Node:
        """
        Return the subnode at the given path, creating it if missing
        """
        if not path:
            return self
        else:
            return self.child(path.head).at_path(path.tail)

    def contains(self, page: Page) -> bool:
        """
        Check if page is contained in or under this node
        """
        # Walk the parent chain of page.node to see if we find self
        node = page.node
        while node is not None:
            if node == self:
                return True
            node = node.parent
        return False

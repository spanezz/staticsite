from __future__ import annotations

import contextlib
import logging
import os
from typing import TYPE_CHECKING, Generator, Optional, Sequence, TextIO, Type, Union

from . import fields
from .site import SiteElement, Path

if TYPE_CHECKING:
    from . import file
    from .asset import Asset
    from .page import Page
    from .site import Site

log = logging.getLogger("node")


class SkipPage(Exception):
    """
    Exception raised when a page should not be added to the site
    """
    pass


class Node(SiteElement):
    """
    One node in the rendered directory hierarchy of the site
    """
    site_path = fields.Field(doc="""
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
        # SourcePages in this node indexed by basename(src.relpath)
        self.by_src_relpath: dict[str, Page] = {}
        # Pages to be rendered at this location
        self.build_pages: dict[str, Page] = {}
        # Subdirectories
        self.sub: dict[str, Node] = {}

    def __repr__(self):
        return f"Node({self.name})"

    def print(self, lead: str = "", file: Optional[TextIO] = None):
        if self.page:
            print(f"{lead}{self.name!r} page:{self.page!r}", file=file)
        else:
            print(f"{lead}{self.name!r} (no page)", file=file)
        for name, page in self.build_pages.items():
            print(f"{lead}- {name} → {page!r}", file=file)
        for name, node in self.sub.items():
            node.print(lead + "+ ", file=file)

    def iter_pages(self, prune: Sequence[Node] = (), source_only: bool = False) -> Generator[Page, None, None]:
        """
        Iterate all pages in this subtree
        """
        # Avoid nodes in prune
        if self in prune:
            return
        if source_only:
            yield from self.by_src_relpath.values()
        else:
            yield from self.build_pages.values()
        for node in self.sub.values():
            yield from node.iter_pages(prune, source_only=source_only)

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
            root = self.site.root
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
        if (subnode := self.sub.get(path.head)) and subnode.page:
            return subnode.page

        # Match subpage names and basename of src.relpath in subpages
        if (page := self.build_pages.get(path.head)) is not None:
            return page
        if (page := self.by_src_relpath.get(path.head)) is not None:
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

    def create_source_page(
            self,
            path: Optional[Path] = None,
            dst: Optional[str] = None,
            directory_index: bool = False,
            **kw):
        """
        Create a page of the given type, attaching it at the given path
        """
        if "created_from" in kw:
            raise RuntimeError("source page created with 'created_from' set")

        if directory_index and dst:
            raise RuntimeError(f"directory_index is True for a page with dst set ({dst=!r})")

        if dst is None and not directory_index and not path:
            raise RuntimeError(f"{self.compute_path()}: empty path for {kw['page_cls']}")

        # TODO: move site.is_page_ignored here?
        try:
            if dst:
                return self._create_leaf_page(dst=dst, path=path, **kw)
            else:
                return self._create_index_page(path=path, directory_index=directory_index,  **kw)
        except SkipPage:
            return None

    def create_auto_page(
            self,
            path: Optional[Path] = None,
            dst: Optional[str] = None,
            directory_index: bool = False,
            **kw):
        """
        Create a page of the given type, attaching it at the given path
        """
        if "src" in kw:
            raise RuntimeError("auto page created with 'src' set")

        if directory_index and dst:
            raise RuntimeError(f"directory_index is True for a page with dst set ({dst=!r})")

        if dst is None and not directory_index and not path:
            raise RuntimeError(f"{self.compute_path()}: empty path for {kw['page_cls']}")

        # TODO: move site.is_page_ignored here?
        try:
            if dst:
                return self._create_leaf_page(dst=dst, path=path, **kw)
            else:
                return self._create_index_page(path=path, directory_index=directory_index,  **kw)
        except SkipPage:
            return None

    def _create_index_page(
            self, *,
            page_cls: Type[Page],
            path: Optional[Path] = None,
            directory_index: bool = False,
            **kw):
        from .page import PageValidationError

        if path:
            # If a subpath is requested, delegate to subnodes
            with self.tentative_child(path.head) as node:
                return node._create_index_page(
                        page_cls=page_cls, path=path.tail,
                        **kw)

        if directory_index:
            search_root_node = self
        else:
            search_root_node = self.parent

        # Create the page
        try:
            page = self.site.features.get_page_class(page_cls)(
                site=self.site, dst="index.html", node=self,
                search_root_node=search_root_node,
                leaf=False,
                directory_index=directory_index, **kw)
        except PageValidationError as e:
            log.warn("%s: skipping page: %s", e.page, e.msg)
            raise SkipPage()
        if self.site.is_page_ignored(page):
            raise SkipPage()

        if self.page is not None:
            if self.page.TYPE == "asset" and page.TYPE == "asset":
                # First one wins, to allow overriding of assets in theme
                pass
            else:
                log.warn("%s: page %r replaces page %r", self.compute_path(), page, self.page)

        self.page = page
        if (src := kw.get("src")) is not None:
            search_root_node.by_src_relpath[os.path.basename(src.relpath)] = page
        self.build_pages["index.html"] = page
        self.site.features.examine_new_page(page)
        # if page.directory_index is False:
        #     print(f"{page=!r} dst is not set but page is not a directory index")
        return page

    def _create_leaf_page(
            self, *,
            page_cls: Type[Page],
            dst: str,
            path: Optional[Path] = None,
            **kw):
        from .page import PageValidationError

        if path:
            # If a subpath is requested, delegate to subnodes
            with self.tentative_child(path.head) as node:
                return node._create_leaf_page(
                        page_cls=page_cls, dst=dst, path=path.tail,
                        **kw)

        # Create the page
        try:
            page = self.site.features.get_page_class(page_cls)(
                site=self.site, dst=dst,
                node=self,
                search_root_node=self,
                leaf=True,
                directory_index=False, **kw)
        except PageValidationError as e:
            log.warn("%s: skipping page: %s", e.page, e.msg)
            raise SkipPage()
        if self.site.is_page_ignored(page):
            raise SkipPage()

        if (old := self.build_pages.get(dst)):
            if old.TYPE == "asset" and page.TYPE == "asset":
                # First one wins, to allow overriding of assets in theme
                pass
            else:
                log.warn("%s: page %r replaces page %r", self.compute_path(), page, old)

        self.build_pages[dst] = page
        if (src := kw.get("src")) is not None:
            self.by_src_relpath[os.path.basename(src.relpath)] = page
        self.site.features.examine_new_page(page)
        return page

    def add_asset(self, *, src: file.File, name: str) -> Asset:
        """
        Add an Asset as a subnode of this one
        """
        # Import here to avoid cyclical imports
        from .asset import Asset
        return self.create_source_page(page_cls=Asset, src=src, name=name, dst=name)

    def add_directory_index(self, src: file.File):
        """
        Add a directory index to this node
        """
        from . import dirindex
        return self.create_source_page(
            page_cls=dirindex.Dir,
            name=self.name,
            src=src,
            directory_index=True)

    @contextlib.contextmanager
    def tentative_child(self, name: str) -> Generator[Node, None, None]:
        """
        Add a child, removing it if an exception is raised
        """
        if (node := self.sub.get(name)):
            yield node
            return

        try:
            node = self.site.features.get_node_class()(site=self.site, name=name, parent=self)
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

        node = self.site.features.get_node_class()(site=self.site, name=name, parent=self)
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

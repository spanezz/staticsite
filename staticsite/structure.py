from __future__ import annotations

import contextlib
import logging
import os
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Generator, Optional, Type

from .metadata import Meta

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


class Node:
    """
    One node in the rendered directory hierarchy of the site
    """
    def __init__(
            self,
            site: Site,
            name: str, *,
            meta: Meta,
            src: Optional[file.File] = None,
            parent: Optional[Node] = None):
        # Pointer to the root structure
        self.site = site
        # Basename of this directory
        self.name: str = name
        # Parent node, or None if this is the root
        self.parent: Optional[Node] = parent
        # Metadata for this directory
        self.meta = meta
        # Set if node corresponds to a source directory in the file system
        self.src: Optional[file.File] = src
        # Index page for this directory, if present
        self.page: Optional[Page] = None
        # Pages to be rendered at this location
        self.build_pages: dict[str, Page] = {}
        # Subdirectories
        self.sub: Optional[dict[str, Node]] = None

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
                # print(f"Node.lookup_page: descend into {subnode.name!r} with {path.tail=!r}")
                return subnode.lookup_page(path.tail)
            else:
                return None

        # Match subnode name
        if self.sub and (subnode := self.sub.get(path.head)) and subnode.page:
            return subnode.page

        # Match basename of src.relpath in subpages
        # TODO: to be reimplemented after leaf pages are in a separate dict
        if self.sub:
            for subnode in self.sub.values():
                if (page := subnode.page) and (src := page.src) and os.path.basename(src.relpath) == path.head:
                    return page
                if (page := subnode.page) and (dst := page.dst) and dst == path.head:
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
            print(f"{self.compute_path()}: empty path for {kw['page_cls']}")

        # TODO: move site.is_page_ignored here?
        try:
            if dst:
                return self._create_leaf_page(dst=dst, path=path, **kw)
            else:
                return self._create_index_page(path=path, directory_index=directory_index, **kw)
        except SkipPage:
            return None

    def _build_page_meta(
            self, page_cls: Type[Page], directory_index: bool,
            meta_values: Optional[dict[str, Any]], created_from: Optional[Page]):
        """
        Build metadata for a page to be created
        """
        from . import dirindex
        if created_from:
            meta = created_from.meta.derive()
            # Invalid invariant: scaled images do have src
            # if src:
            #     print(f"{created_from=!r} and {src=!r}")
        elif directory_index and page_cls != dirindex.Dir:
            meta = self.meta
        else:
            meta = self.meta.derive()
        if meta_values:
            meta.update(meta_values)
        if created_from:
            meta["created_from"] = created_from
        return meta

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

        meta = self._build_page_meta(
                page_cls=page_cls, directory_index=directory_index,
                meta_values=meta_values, created_from=created_from)

        if directory_index:
            search_root_node = self
        else:
            search_root_node = self.parent

        # Create the page
        page = page_cls(
            site=self.site, src=src, dst="index.html", node=self,
            search_root_node=search_root_node,
            directory_index=directory_index, meta=meta, **kw)
        if self.site.is_page_ignored(page):
            raise SkipPage()
        if self.src is None:
            self.src = src

        # TODO: Move under 'if not dst'
        self.page = page
        self.site.structure.index(page)
        # if page.directory_index is False:
        #     print(f"{page=!r} dst is not set but page is not a directory index")

        page.build_node = self.child("index.html")
        page.build_node.page = page
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

        meta = self._build_page_meta(
                page_cls=page_cls, directory_index=False,
                meta_values=meta_values, created_from=created_from)

        dest_node = self.child(dst)

        # Create the page
        page = page_cls(
            site=self.site, src=src, dst=dst,
            # TODO: switch to just self once we get rid of structure.pages:
            # this is only needed to get a good site_path there
            node=dest_node,
            search_root_node=self,
            directory_index=False, meta=meta, **kw)
        if self.site.is_page_ignored(page):
            raise SkipPage()
        if self.src is None:
            self.src = src

        dest_node.page = page
        self.site.structure.index(page)
        return page

    def add_asset(self, *, src: file.File, name: str) -> Asset:
        """
        Add an Asset as a subnode of this one
        """
        # Import here to avoid cyclical imports
        from .asset import Asset
        return self.create_page(page_cls=Asset, src=src, name=name, dst=name)

    def add_directory_index(self):
        """
        Add a directory index to this node
        """
        from . import dirindex
        return self.create_page(
            page_cls=dirindex.Dir,
            name=self.name,
            directory_index=True,
            src=self.src)

    @contextlib.contextmanager
    def tentative_child(self, name: str, *, src: Optional[file.File] = None) -> Generator[Node, None, None]:
        """
        Add a child, removing it if an exception is raised
        """
        if self.sub and (node := self.sub.get(name)):
            if src and not node.src:
                node.src = src
            yield node
            return

        try:
            if self.sub is None:
                self.sub = {}

            node = Node(site=self.site, name=name, parent=self, src=src, meta=self.meta.derive())
            self.sub[name] = node
            yield node
        except Exception:
            # Rollback the addition
            self.sub.pop(name, None)
            if not self.sub:
                self.sub = None

    def child(self, name: str, *, src: Optional[file.File] = None) -> Node:
        """
        Return the given subnode, creating it if missing
        """
        if self.sub is None:
            self.sub = {}

        if (node := self.sub.get(name)):
            if src and not node.src:
                node.src = src
            return node

        node = Node(site=self.site, name=name, parent=self, src=src, meta=self.meta.derive())
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


class Structure:
    """
    Track and index the site structure
    """
    def __init__(self, site: Site):
        self.site = site

        # Root directory of the site
        self.root = Node(site, "", meta=Meta(site.metadata))

        # Site pages indexed by site_path
        self.pages: dict[str, Page] = {}

        # Site pages that have the given metadata
        self.pages_by_metadata: dict[str, list[Page]] = defaultdict(list)

        # Metadata for which we add pages to pages_by_metadata
        self.tracked_metadata: set[str] = set()

    def add_tracked_metadata(self, name: str):
        """
        Mark the given metadata name so that we track pages that have it.

        Reindex existing pages, if any
        """
        if name in self.tracked_metadata:
            return

        self.tracked_metadata.add(name)

        # Redo indexing for existing pages
        for page in self.pages.values():
            if name in page.meta.values:
                self.pages_by_metadata[name].append(page)

    def index(self, page: Page):
        """
        Register a new page in the site
        """
        # Mount page by site path
        site_path = page.site_path
        old = self.pages.get(site_path)
        if old is not None:
            if old.TYPE == "asset" and page.TYPE == "asset":
                # First one wins, to allow overriding of assets in theme
                pass
            else:
                log.warn("%s: page %r replaces page %r", site_path, page, old)
        self.pages[site_path] = page

        # Also group pages by tracked metadata
        for tracked in self.tracked_metadata:
            if tracked in page.meta.values:
                self.pages_by_metadata[tracked].append(page)

    def analyze(self):
        """
        Iterate through all Pages in the site to build aggregated content like
        taxonomies and directory indices.

        Call this after all Pages have been added to the site.
        """
        # Add missing pages_by_metadata entries in case no matching page were
        # found for some of them
        for key in self.tracked_metadata:
            if key not in self.pages_by_metadata:
                self.pages_by_metadata[key] = []

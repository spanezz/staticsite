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

    def compute_path(self) -> str:
        """
        Compute the build path for this node
        """
        if self.parent is None:
            return self.name
        else:
            return os.path.join(self.parent.compute_path(), self.name)

    def create_page(self, **kw):
        """
        Create a page of the given type, attaching it at the given path
        """
        if "meta" in kw:
            raise RuntimeError("do not pass meta to create_page")

        # TODO: move site.is_page_ignored here?
        try:
            return self._create_page(**kw)
        except SkipPage:
            return None

    def _create_page(
            self, *,
            page_cls: Type[Page],
            src: Optional[file.File] = None,
            path: Optional[Path] = None,
            build_as: Optional[Path] = None,
            directory_index: bool = False,
            meta_values: Optional[dict[str, Any]] = None,
            created_from: Optional[Page] = None,
            # If True, show as path (i.e. name/index.html), if False as file
            # (i.e. name.jpg)
            as_path: bool,
            **kw):
        from . import dirindex
        if path:
            # If a subpath is requested, delegate to subnodes
            with self.tentative_child(path.head) as node:
                return node.create_page(
                        page_cls=page_cls, src=src, path=path.tail,
                        build_as=build_as, directory_index=directory_index,
                        meta_values=meta_values, created_from=created_from,
                        as_path=as_path,
                        **kw)

        # Create the page, with some dependency injection
        if created_from:
            meta = created_from.meta.derive()
            if src is None:
                src = created_from.src
        elif directory_index and page_cls != dirindex.Dir:
            meta = self.meta
        else:
            meta = self.meta.derive()
        if meta_values:
            meta.update(meta_values)
        if created_from:
            meta["created_from"] = created_from
        page = page_cls(site=self.site, src=src, node=self, directory_index=directory_index, meta=meta, **kw)
        if self.site.is_page_ignored(page):
            raise SkipPage()
        if self.src is None:
            self.src = src
        self.page = page
        self.site.structure.index(page)
        if build_as:
            page.build_node = self.at_path(build_as)
            page.build_node.page = page
        return page

    def add_asset(self, *, src: file.File, name: str) -> Asset:
        """
        Add an Asset as a subnode of this one
        """
        # Import here to avoid cyclical imports
        from .asset import Asset
        return self.child(name, src=src).create_page(page_cls=Asset, src=src, name=name, as_path=False)

    def add_directory_index(self):
        """
        Add a directory index to this node
        """
        from . import dirindex
        return self.create_page(
            page_cls=dirindex.Dir,
            name=self.name,
            directory_index=True,
            as_path=True,
            src=self.src,
            build_as=Path(("index.html",)))

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

        # Site pages indexed by src.relpath
        self.pages_by_src_relpath: dict[str, Page] = {}

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

        # Mount page by src.relpath
        # Skip pages derived from other pages, or they would overwrite them
        if page.src is not None and not page.created_from:
            self.pages_by_src_relpath[page.src.relpath] = page

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

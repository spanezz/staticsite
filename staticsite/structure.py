from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .page import Page
    from .site import Site
    from .asset import Asset
    from . import file
    from .metadata import Meta

log = logging.getLogger("structure")


re_pathsep = re.compile(re.escape(os.pathsep) + "+")


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
        return cls(re_pathsep.split(path.strip(os.pathsep)))


class Node:
    """
    One node in the rendered directory hierarchy of the site
    """
    def __init__(
            self,
            site: Site,
            name: str, *,
            src: Optional[file.File] = None,
            parent: Optional[Node] = None):
        # Pointer to the root structure
        self.site = site
        # Basename of this directory
        self.name: str = name
        # Parent node, or None if this is the root
        self.parent: Optional[Node] = parent
        # Set if node corresponds to a source directory in the file system
        self.src: Optional[file.File] = src
        # Index page for this directory, if present
        self.page: Optional[Page] = None
        # Subdirectories
        self.sub: Optional[dict[str, Node]] = None

    def add_page(self, page: Page, *, src: Optional[file.File] = None, name: Optional[str] = None):
        """
        Add a page as a subnode of this one, or as the page of this one if name is None
        """
        if self.site.is_page_ignored(page):
            return

        if name is None:
            self._attach_page(page)
        else:
            self.child(name, src=src)._attach_page(page)

    def add_asset(self, *, src: file.File, name: str, parent_meta: Optional[Meta] = None) -> Asset:
        """
        Add an Asset as a subnode of this one
        """
        # Import here to avoid cyclical imports
        from .asset import Asset
        if parent_meta is None:
            parent_meta = self.page.meta
        page = Asset.create(site=self.site, src=src, parent_meta=parent_meta, name=name)
        self.child(name, src=src)._attach_page(page)
        return page

    def _attach_page(self, page: Page):
        """
        Attach a page to this node
        """
        page.node = self
        self.page = page
        self.site.structure.index(page)

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

        node = Node(site=self.site, name=name, parent=self, src=src)
        self.sub[name] = node
        return node

    def add_generated_page(self, page: Page, path: Path):
        """
        Add a page with the given path to this directory structure
        """
        if path:
            self.child(path.head).add_generated_page(page, path.tail)
        elif self.page is not None:
            log.warning(
                    "Autogenerated page %r should be mounted where there is already page %r: ignored",
                    page, self.page)
        else:
            # Add/replace as index for this entry
            self._attach_page(page)


class Structure:
    """
    Track and index the site structure
    """
    def __init__(self, site: Site):
        self.site = site

        # Root directory of the site
        self.root = Node(site, "")

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
            if name in page.meta:
                self.pages_by_metadata[name].append(page)

    def add_generated_page(self, page: Page, site_path: str):
        """
        Add a generated page at the given path
        """
        if self.site.is_page_ignored(page):
            return

        self.root.add_generated_page(page, Path.from_string(site_path))

    def index(self, page: Page):
        """
        Register a new page in the site
        """
        # Mount page by site path
        site_path = page.meta["site_path"]
        old = self.pages.get(site_path)
        if old is not None:
            if old.TYPE == "asset" and page.TYPE == "asset":
                pass
            # elif old.TYPE == "dir" and page.TYPE not in ("dir", "asset"):
            #     pass
            else:
                log.warn("%s: replacing page %s", page, old)
        self.pages[site_path] = page

        # Mount page by src.relpath
        # Skip pages derived from other pages, or they would overwrite them
        if page.src is not None and not page.created_from:
            self.pages_by_src_relpath[page.src.relpath] = page

        # Also group pages by tracked metadata
        for tracked in self.tracked_metadata:
            if tracked in page.meta:
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

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .page import Page
    from .site import Site

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


class Entry:
    """
    One node in the rendered directory hierarchy of the site
    """
    def __init__(self, name: str):
        # Basename of this directory
        self.name = name
        # Index page for this directory, if present
        self.page: Optional[Page] = None
        # Subdirectories
        self.sub: Optional[dict[str, Entry]] = None

    def add_page(self, page: Page, path: Path):
        """
        Add a page with the given path to this directory structure
        """
        if not path:
            # Add/replace as index for this entry
            self.page = page
            return

        # Add as sub-entry
        if self.sub is None:
            self.sub = {}

        if (entry := self.sub.get(path.head)) is None:
            entry = Entry(path.head)
            self.sub[path.head] = entry

        entry.add_page(page, path.tail)


class Structure:
    """
    Track and index the site structure
    """
    def __init__(self, site: Site):
        # Root directory of the site
        self.root = Entry("")

        # Site pages indexed by site_path
        self.pages: dict[str, Page] = {}

        # Site pages that have the given metadata
        self.pages_by_metadata: dict[str, list[Page]] = defaultdict(list)

        # Metadata for which we add pages to pages_by_metadata
        self.tracked_metadata: set[str] = set()

        # Site pages indexed by src.relpath
        self.pages_by_src_relpath: dict[str, Page] = {}

    def add_page(self, page: Page):
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

        # Add to site structure
        path = Path.from_string(site_path)
        self.root.add_page(page, path)

        # Mount page by src.relpath
        # Skip pages derived from other pages, or they would overwrite them
        if page.src is not None and not page.created_from:
            self.pages_by_src_relpath[page.src.relpath] = page

        # Also group pages by tracked metadata
        for tracked in page.meta.keys() & self.tracked_metadata:
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

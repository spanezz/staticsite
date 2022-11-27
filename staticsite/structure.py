from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .site import Site
    from .page import Page

log = logging.getLogger("structure")


class Structure:
    """
    Track and index the site structure
    """
    def __init__(self, site: Site):
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

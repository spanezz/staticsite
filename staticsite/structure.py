from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from .node import Node
# TODO: remove this, which is here only for compatibility
from .node import Path  # noqa

if TYPE_CHECKING:
    from .page import Page
    from .site import Site

log = logging.getLogger("structure")


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

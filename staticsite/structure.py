from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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

        # Site pages that have the given metadata
        self.pages_by_metadata: dict[str, list[Page]] = {}

    def add_tracked_metadata(self, name: str):
        """
        Mark the given metadata name so that we track pages that have it.

        Reindex existing pages, if any
        """
        if name in self.pages_by_metadata:
            return
        self.pages_by_metadata[name] = []

    def index(self, page: Page):
        """
        Register a new page in the site
        """
        # Also group pages by tracked metadata
        for name, pages in self.pages_by_metadata.items():
            if name in page.__dict__:
                pages.append(page)

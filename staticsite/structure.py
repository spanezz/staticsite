from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .site import Site
    from .page import Page


class Structure:
    """
    Track and index the site structure
    """
    def __init__(self, site: Site):
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
        # Mount page by src.relpath
        # Skip pages derived from other pages, or they would overwrite them
        if page.src is not None and not page.created_from:
            self.pages_by_src_relpath[page.src.relpath] = page

        # Also group pages by tracked metadata
        for tracked in page.meta.keys() & self.tracked_metadata:
            self.pages_by_metadata[tracked].append(page)

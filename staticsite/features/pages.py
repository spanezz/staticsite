from __future__ import annotations

import logging
from typing import Any, Sequence, Type, Union

from staticsite.feature import Feature, PageTrackingMixin, TrackedField
from staticsite.page import ChangeExtent, Page, SourcePage

log = logging.getLogger("pages")


class PagesField(TrackedField["PagesPageMixin", Union[str, dict[str, Any], list[Page]]]):
    """
    The `pages` metadata can use to select a set of pages shown by the current
    page. Although default `page.html` template will not do anything with them,
    other page templates, like `blog.html`, use this to select the pages to show.

    The `pages` feature allows defining a [page filter](page-filter.md) in the
    `pages` metadata element, which will be replaced with a list of matching pages.

    To select pages, the `pages` metadata is set to a dictionary that select pages
    in the site, with the `path`, and taxonomy names arguments similar to the
    `site_pages` function in [templates](templates.md).

    See [Selecting pages](page-filter.md) for details.
    """
    tracked_by = "pages"


class PagesPageMixin(Page):
    pages = PagesField(structure=True)


class PagesSourcePageMixin(PagesPageMixin, SourcePage):
    def _compute_footprint(self) -> dict[str, Any]:
        res = super()._compute_footprint()
        if self.pages:
            res["pages"] = [page.src.relpath for page in self.pages if getattr(page, "src", None)]
        return res

    def _compute_change_extent(self) -> ChangeExtent:
        res = super()._compute_change_extent()
        if self.old_footprint is None:
            return ChangeExtent.ALL
        if "footprint" in self._fields and res == ChangeExtent.UNCHANGED:
            if set(self.footprint.get("pages", ())) != set(self.old_footprint.get("pages", ())):
                res = ChangeExtent.ALL
        return res


class PagesFeature(PageTrackingMixin, Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    def get_page_bases(self, page_cls: Type[Page]) -> Sequence[Type[Page]]:
        if issubclass(page_cls, SourcePage):
            return (PagesSourcePageMixin,)
        else:
            return (PagesPageMixin,)

    def crossreference(self):
        # Expand pages expressions
        for page in self.tracked_pages:
            query = page.pages
            if isinstance(query, str):
                query = {"path": query}
            elif not isinstance(query, dict):
                # Skip pages that already have a populated pages list
                continue
            # print("FILTER", pages)

            # Replace the dict with the expanded list of pages
            # Do not include self in the result list
            pages = [p for p in page.find_pages(**query) if p != page]
            # print(f"pages {page=!r}, {query=!r}, {pages=}")
            page.pages = pages
            if pages:
                max_date = max(p.date for p in pages)

                # Update the page date to the max of the pages dates
                page.date = max(max_date, page.date)


FEATURES = {
    "pages": PagesFeature,
}

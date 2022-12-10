from __future__ import annotations

import logging

from staticsite import fields
from staticsite.feature import Feature

log = logging.getLogger("pages")


class PagesPageMixin(metaclass=fields.FieldsMetaclass):
    pages = fields.Field(structure=True, doc="""
        The `pages` metadata can use to select a set of pages shown by the current
        page. Although default `page.html` template will not do anything with them,
        other page templates, like `blog.html`, use this to select the pages to show.

        The `pages` feature allows defining a [page filter](page-filter.md) in the
        `pages` metadata element, which will be replaced with a list of matching pages.

        To select pages, the `pages` metadata is set to a dictionary that select pages
        in the site, with the `path`, and taxonomy names arguments similar to the
        `site_pages` function in [templates](templates.md).

        See [Selecting pages](page-filter.md) for details.
    """)


class PagesFeature(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.page_mixins = (PagesPageMixin,)
        self.site.features.add_tracked_metadata("pages")

    def organize(self):
        # Expand pages expressions
        for page in self.site.features.pages_by_metadata["pages"]:
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

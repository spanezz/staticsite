from __future__ import annotations
from staticsite.feature import Feature
from staticsite.metadata import Metadata
import logging

log = logging.getLogger("pages")


class PagesFeature(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site.structure.tracked_metadata.add("pages")
        self.site.register_metadata(Metadata("pages", structure=True, doc="""
The `pages` metadata can use to select a set of pages shown by the current
page. Although default `page.html` template will not do anything with them,
other page templates, like `blog.html`, use this to select the pages to show.

The `pages` feature allows defining a [page filter](page-filter.md) in the
`pages` metadata element, which will be replaced with a list of matching pages.

To select pages, the `pages` metadata is set to a dictionary that select pages
in the site, with the `path`, and taxonomy names arguments similar to the
`site_pages` function in [templates](templates.md).

See [Selecting pages](page-filter.md) for details.
"""))

    def analyze(self):
        # Expand pages expressions
        for page in self.site.structure.pages_by_metadata["pages"]:
            pages = page.meta["pages"]
            if isinstance(pages, str):
                pages = {"path": pages}
            elif not isinstance(pages, dict):
                # Skip pages that already have a populated pages list
                continue

            # Replace the dict with the expanded list of pages
            # Do not include self in the result list
            pages = [p for p in page.find_pages(**pages) if p != page]
            page.meta["pages"] = pages
            if pages:
                max_date = max(p.meta["date"] for p in pages)

                # Update the page date to the max of the pages dates
                page.meta["date"] = max(max_date, page.meta["date"])


FEATURES = {
    "pages": PagesFeature,
}

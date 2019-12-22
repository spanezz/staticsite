from __future__ import annotations
from staticsite.feature import Feature
from staticsite.theme import PageFilter
from staticsite.metadata import Metadata
import logging

log = logging.getLogger("pages")


class PagesFeature(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site.tracked_metadata.add("pages")
        self.site.register_metadata(Metadata("syndication", inherited=False, structure=True, doc=f"""
If using the [pages](pages.md) feature, or for taxonomy or syndication pages,
this is a list of pages selected by the current page.

The `pages` feature allows defining a [page filter](page-filter.md) in the
`pages` metadata element, which will be replaced with a list of matching pages.

To select pages, the `pages` metadata is set to a dictionary that select pages
in the site, similar to the `site_pages` function in [templates](templates.md),
and to [`filter` in syndication](syndication.md).

See [Selecting pages](page-filter.md) for details.
"""))

    def finalize(self):
        # Expand pages expressions
        for page in self.site.pages_by_metadata["pages"]:
            pages = page.meta["pages"]
            # Skip pages that already have a populated pages list
            if not isinstance(pages, dict):
                continue

            # Replace the dict with the expanded list of pages
            f = PageFilter(self.site, **pages)
            page.meta["pages"] = f.filter(self.site.pages.values())


FEATURES = {
    "pages": PagesFeature,
}

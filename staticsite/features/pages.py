from __future__ import annotations
from staticsite.feature import Feature
from staticsite.theme import PageFilter
from staticsite.contents import ContentDir
import logging

log = logging.getLogger("pages")


class PagesFeature(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site.tracked_metadata.add("pages")

    def load_dir_meta(self, sitedir: ContentDir):
        # Remove 'pages' from directory metadata, to avoid propagating
        # the toplevel page filter data to the rest of the site.
        sitedir.meta.pop("pages", None)

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

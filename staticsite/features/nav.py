from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from staticsite import metadata
from staticsite.feature import Feature
from staticsite.page import PageNotFoundError

if TYPE_CHECKING:
    from staticsite.page import Page

log = logging.getLogger("nav")


class Nav(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    RUN_AFTER = ["autogenerated_pages"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site.register_metadata(metadata.MetadataInherited("nav", structure=True, doc="""
List of page paths that are used for the navbar.
"""))
        self.site.structure.add_tracked_metadata("nav")

        self.site.register_metadata(metadata.Metadata("nav_title", doc="""
Title to use when this page is linked in a navbar.

It defaults to `page.meta.title`, or to the series name for series pages.

`nav_title` is only guaranteed to exist for pages that are used in `nav`.
"""))

    def analyze(self):
        # Expand pages expressions
        nav_pages: set[Page] = set()

        for page in self.site.structure.pages_by_metadata["syndication"]:
            if (nav := page.meta.values.get("nav")) is None:
                continue

            # Resolve everything as pages
            this_nav = []
            for path in nav:
                try:
                    this_nav.append(page.resolve_path(path))
                except PageNotFoundError as e:
                    log.warn("%s: %s", page, e)

            # print(f"{page!r} nav={this_nav!r}")

            # Build list of target pages
            nav_pages.update(this_nav)

            page.meta.values["nav"] = this_nav

        # Make sure nav_title is filled
        for page in nav_pages:
            if "nav_title" not in page.meta:
                page.meta["nav_title"] = page.meta["title"]


FEATURES = {
    "nav": Nav,
}

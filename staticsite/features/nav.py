from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from staticsite import metadata
from staticsite.feature import Feature
from staticsite.page import PageNotFoundError

if TYPE_CHECKING:
    from staticsite.page import Page

log = logging.getLogger("nav")


class NavData:
    def __init__(self, page: Page, paths: list[str]):
        self.page = page
        self.paths = paths
        self.resolved: Optional[list[Page]] = None

    def _resolve(self):
        if self.resolved is not None:
            return
        self.resolved = [self.page.resolve_path(path) for path in self.paths]

    def __iter__(self):
        self._resolve()
        return self.resolved.__iter__()

    def to_dict(self):
        self._resolve()
        return self.resolved


class MetadataNav(metadata.MetadataInherited):
    def set(self, obj: metadata.SiteElement, values: dict[str, Any]):
        """
        Set metadata values in obj from values
        """
        # Create a NavData element from the value set
        if (val := values.get(self.name)):
            obj.meta.values[self.name] = NavData(obj, val)

    # def prepare_to_render(self, obj: metadata.SiteElement):
    #     """
    #     Compute values before the SiteElement gets rendered
    #     """


class NavMixin(metaclass=metadata.FieldsMetaclass):
    nav = MetadataNav(structure=True, doc="""
        List of page paths, relative to the page defining the nav element, that
        are used for the navbar.
    """)


class NavPageMixin(NavMixin):
    nav_title = metadata.Metadata(doc="""
        Title to use when this page is linked in a navbar.

        It defaults to `page.meta.title`, or to the series name for series pages.

        `nav_title` is only guaranteed to exist for pages that are used in `nav`.
    """)


class Nav(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    RUN_AFTER = ["autogenerated_pages"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.node_mixins.append(NavMixin)
        self.page_mixins.append(NavPageMixin)
        self.site.structure.add_tracked_metadata("nav")

    def analyze(self):
        # Expand pages expressions
        nav_pages: set[Page] = set()

        for page in self.site.structure.pages_by_metadata["nav"]:
            if (nav := page.meta.get("nav")) is None:
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

            page.meta["nav"] = this_nav

        # Make sure nav_title is filled
        for page in nav_pages:
            if "nav_title" not in page.meta:
                page.prepare_render()
                page.meta["nav_title"] = page.meta["title"]


FEATURES = {
    "nav": Nav,
}

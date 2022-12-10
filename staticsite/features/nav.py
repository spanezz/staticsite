from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from staticsite import fields, metadata
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
        self.resolved = []
        for path in self.paths:
            try:
                page = self.page.resolve_path(path)
            except PageNotFoundError as e:
                log.warning("%r: skipping page in nav: %s", self.page, e)
                continue
            if page is None:
                log.warning("%r: path %r resolved as None: skipping", self.page, path)
                continue
            self.resolved.append(page)

    def __iter__(self):
        self._resolve()
        return self.resolved.__iter__()

    def to_dict(self):
        self._resolve()
        return self.resolved


class NavField(fields.Inherited):
    def __init__(self, **kw):
        kw.setdefault("default", ())
        super().__init__(**kw)

    def _clean(self, obj: metadata.SiteElement, value: Any) -> NavData:
        """
        Set metadata values in obj from values
        """
        return NavData(obj, value)


class NavMixin(metaclass=fields.FieldsMetaclass):
    nav = NavField(structure=True, doc="""
        List of page paths, relative to the page defining the nav element, that
        are used for the navbar.
    """)


class NavPageMixin(NavMixin):
    nav_title = fields.Field(doc="""
        Title to use when this page is linked in a navbar.

        It defaults to `page.title`, or to the series name for series pages.

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
            if (nav := page.nav) is None:
                continue

            # Resolve paths to target pages
            nav._resolve()

            # Build list of target pages
            nav_pages.update(nav.resolved)

        # Make sure nav_title is filled
        for page in nav_pages:
            if not page.nav_title:
                page.nav_title = page.title


FEATURES = {
    "nav": Nav,
}

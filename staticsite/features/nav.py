from __future__ import annotations

import logging
from typing import Any, Iterator, Optional, Sequence, Type

from staticsite import fields
from staticsite.feature import Feature, PageTrackingMixin, TrackedField
from staticsite.node import Node
from staticsite.page import Page, PageNotFoundError

log = logging.getLogger("nav")


class NavData:
    def __init__(self, page: Page, paths: list[str]):
        self.page = page
        self.paths = paths
        self.resolved: Optional[list["NavPageMixin"]] = None

    def _resolve(self) -> None:
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

    def __iter__(self) -> Iterator["NavPageMixin"]:
        self._resolve()
        return self.resolved.__iter__()

    def to_dict(self) -> list["NavPageMixin"]:
        self._resolve()
        return self.resolved


class NavField(TrackedField[Page, NavData]):
    """
    List of page paths, relative to the page defining the nav element, that
    are used for the navbar.
    """
    tracked_by = "nav"

    def __init__(self, **kw: Any):
        kw.setdefault("inherited", True)
        kw.setdefault("default", ())
        super().__init__(**kw)

    def _clean(self, page: Page, value: Any) -> NavData:
        """
        Set metadata values in obj from values
        """
        return NavData(page, value)


class NavNodeMixin(Node):
    nav = NavField(structure=True)


class NavPageMixin(Page):
    nav = NavField(structure=True)
    nav_title = fields.Str[Page](doc="""
        Title to use when this page is linked in a navbar.

        It defaults to `page.title`, or to the series name for series pages.

        `nav_title` is only guaranteed to exist for pages that are used in `nav`.
    """)


class Nav(PageTrackingMixin[NavPageMixin], Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    def get_node_bases(self) -> Sequence[Type[Node]]:
        return (NavNodeMixin,)

    def get_page_bases(self, page_cls: Type[Page]) -> Sequence[Type[Page]]:
        return (NavPageMixin,)

    def crossreference(self) -> None:
        # Expand pages expressions
        nav_pages: set[NavPageMixin] = set()

        for page in self.tracked_pages:
            if (nav := page.nav) is None:
                continue

            # Resolve paths to target pages
            nav._resolve()

            # Build list of target pages
            if nav.resolved is not None:
                nav_pages.update(nav.resolved)

        # Make sure nav_title is filled
        for target in nav_pages:
            if not target.nav_title:
                target.nav_title = target.title


FEATURES = {
    "nav": Nav,
}

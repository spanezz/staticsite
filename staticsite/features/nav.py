from __future__ import annotations
# from typing import TYPE_CHECKING
from staticsite.page import Page, PageNotFoundError
from staticsite.feature import Feature
from staticsite import metadata
import os
import logging

log = logging.getLogger("nav")


class MetadataNav(metadata.MetadataInherited):
    def __init__(self, *args, **kw):
        kw.setdefault("structure", True)
        super().__init__(*args, **kw)

    def on_dir_meta(self, page: Page, meta):
        """
        Inherited metadata are copied from directory indices into directory
        metadata
        """
        val = meta.get(self.name)
        if val is not None:
            page.meta[self.name] = val
            return

        if page.dir is None:
            return

        val = page.dir.meta.get(self.name)
        if val is None:
            return

        res = []
        for path in val:
            if isinstance(path, str):
                try:
                    path = page.dir.resolve_path(path)
                except PageNotFoundError:
                    path = os.path.join("..", path)
            res.append(path)

        page.meta[self.name] = res

    def on_load(self, page: Page):
        if self.name in page.meta:
            return

        parent = page.dir
        if parent is None:
            return

        val = parent.meta.get(self.name)
        if val is None:
            return

        res = []
        for path in val:
            if isinstance(path, str):
                try:
                    path = parent.resolve_path(path)
                except PageNotFoundError:
                    pass
            res.append(path)

        # print("INHERIT", self.name, "FOR", page, "FROM", parent, "AS", val, "->", res)

        page.meta[self.name] = res


class Nav(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    RUN_AFTER = ["autogenerated_pages"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site.register_metadata(MetadataNav("nav", doc=f"""
List of page paths that are used for the navbar.
"""))
        self.site.register_metadata(metadata.Metadata("nav_title", doc=f"""
Title to use when this paged is linked in a navbar.

It defaults to `page.meta.title`, or to the series name for series pages.

`nav_title` is only guaranteed to exist for pages that are used in `nav`.
"""))

    def finalize(self):
        # Expand pages expressions
        nav_pages = set()

        for page in self.site.pages.values():
            nav = page.meta.get("nav")
            if nav is None:
                continue

            # Resolve everything
            this_nav = []
            for path in nav:
                try:
                    this_nav.append(page.resolve_path(path))
                except PageNotFoundError as e:
                    log.warn("%s: %s", page, e)

            # Build list of target pages
            nav_pages.update(this_nav)

            page.meta["nav"] = this_nav

        # Make sure nav_title is filled
        for page in nav_pages:
            if "nav_title" not in page.meta:
                page.meta["nav_title"] = page.meta["title"]


FEATURES = {
    "nav": Nav,
}

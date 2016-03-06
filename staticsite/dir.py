# coding: utf-8

from .core import Page, settings, RenderedString
import os
import re
from collections import defaultdict
import jinja2
import logging

log = logging.getLogger()

class DirPage(Page):
    """
    A directory index
    """
    TYPE = "dir"
    ANALYZE_PASS = 3
    RENDER_PREFERRED_ORDER = 2

    def __init__(self, site, relpath, pages):
        super().__init__(
            site=site,
            root_abspath=None,
            src_relpath=relpath,
            src_linkpath=relpath,
            dst_relpath=os.path.join(relpath, "index.html"),
            dst_link=os.path.join(settings.SITE_ROOT, relpath))

        self.pages = list(pages)
        self.subdirs = []

    def add_subdir(self, page):
        self.subdirs.append(page)

    @property
    def src_abspath(self):
        return None

    def get_date(self):
        # Sort by decreasing date
        res = self.meta.get("date", None)
        if res is None:
            self.pages.sort(key=lambda x:x.meta["date"], reverse=True)
            res = self.pages[0]
            res = max([res.meta["date"]] + [d.get_date() for d in self.subdirs])
            self.meta["date"] = res
        return res

    def read_metadata(self):
        self.meta["date"] = self.get_date()
        self.meta["title"] = os.path.basename(self.src_relpath) or settings.SITE_NAME

    def render(self):
        body = self.site.dir_template.render(
            page=self,
            pages=self.pages,
        )
        return {
            self.dst_relpath: RenderedString(body)
        }

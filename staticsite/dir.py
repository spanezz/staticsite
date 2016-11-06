# coding: utf-8

from .core import Page, RenderedString
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
            dst_link=os.path.join(site.settings.SITE_ROOT, relpath))

        self.pages = list(pages)
        self.subdirs = []

    def attach_to_parent(self):
        if not self.src_relpath: return
        parent_relpath = os.path.dirname(self.src_relpath)
        parent = self.site.pages[parent_relpath]
        if parent.TYPE != "dir": return
        if self in parent.subdirs: return
        parent.subdirs.append(self)
        parent.attach_to_parent()

    @property
    def src_abspath(self):
        return None

    def get_date(self):
        # Sort by decreasing date
        res = self.meta.get("date", None)
        if res is None:
            self.pages.sort(key=lambda x:x.meta["date"], reverse=True)
            if self.pages:
                dates = [self.pages[0].meta["date"]]
            else:
                dates = []
            dates.extend(d.get_date() for d in self.subdirs)
            self.meta["date"] = res = max(dates)
        return res

    def read_metadata(self):
        self.meta["date"] = self.get_date()
        self.meta["title"] = os.path.basename(self.src_relpath) or self.site.settings.SITE_NAME

    def render(self):
        self.subdirs.sort(key=lambda x:x.meta["title"])
        parent_page = None
        if self.src_relpath:
            parent = os.path.dirname(self.src_relpath)
            parent_page = self.site.pages.get(parent, None)

        body = self.site.theme.dir_template.render(
            parent_page=parent_page,
            page=self,
            pages=self.subdirs + self.pages,
        )
        return {
            self.dst_relpath: RenderedString(body)
        }

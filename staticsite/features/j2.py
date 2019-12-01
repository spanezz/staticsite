from __future__ import annotations
from typing import List
from staticsite.page import Page
from staticsite.render import RenderedString
from staticsite.feature import Feature
from staticsite.file import File, Dir
import os
import logging

log = logging.getLogger()


class IgnorePage(Exception):
    pass


class J2Pages(Feature):
    """
    Render jinja2 templates from the contents directory.

    See doc/templates.md for details.
    """
    RUN_BEFORE = ["tags"]

    def load_dir(self, sitedir: Dir) -> List[Page]:
        meta = sitedir.meta_features.get("j2")
        if meta is None:
            meta = {}

        taken = []
        pages = []
        for fname, f in sitedir.files.items():
            if ".j2." not in fname:
                continue

            try:
                page = J2Page(self, f)
            except IgnorePage:
                continue

            taken.append(fname)
            pages.append(page)

        for fname in taken:
            del sitedir.files[fname]

        return pages


class J2Page(Page):
    TYPE = "jinja2"

    RENDER_PREFERRED_ORDER = 2

    def __init__(self, j2env, src):
        dirname, basename = os.path.split(src.relpath)
        dst_basename = basename.replace(".j2", "")
        dst_relpath = os.path.join(dirname, dst_basename)

        if dst_basename == "index.html":
            linkpath = dirname
        else:
            linkpath = os.path.join(dirname, dst_basename)

        super().__init__(
            site=j2env.site,
            src=src,
            src_linkpath=linkpath,
            dst_relpath=dst_relpath,
            dst_link=os.path.join(j2env.site.settings.SITE_ROOT, linkpath))

        self.meta["date"] = self.site.generation_time

    def render(self):
        try:
            template = self.site.theme.jinja2.get_template(self.src.relpath)
        except Exception:
            log.exception("%s: cannot load template", self.src.relpath)
            raise IgnorePage
        body = self.render_template(template)
        return {
            self.dst_relpath: RenderedString(body),
        }


FEATURES = {
    "j2": J2Pages,
}

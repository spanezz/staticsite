# coding: utf-8

from .core import Archetype, Page, RenderedString, settings
import os
import re
from collections import defaultdict
import logging

log = logging.getLogger()


class IgnorePage(Exception):
    pass


class J2Pages:
    def __init__(self, j2env):
        self.jinja2 = j2env

    def try_load_page(self, site, root_abspath, relpath):
        basename = os.path.basename(relpath)
        if ".j2." not in basename: return None
        try:
            return J2Page(self, site, root_abspath, relpath)
        except IgnorePage:
            return None


class J2Page(Page):
    TYPE = "jinja2"

    RENDER_PREFERRED_ORDER = 2

    def __init__(self, j2env, site, root_abspath, relpath):
        super().__init__(site, root_abspath, relpath)
        self.jinja2 = j2env.jinja2
        basename = os.path.basename(self.src_relpath)
        dirname = os.path.dirname(self.src_relpath)
        self.dst_relpath = os.path.join(dirname, basename.replace(".j2", ""))
        if os.path.basename(self.dst_relpath) == "index.html":
            self.link_relpath = os.path.dirname(self.dst_relpath)
        else:
            self.link_relpath = self.dst_relpath
        self.dst_link = os.path.join(settings.SITE_ROOT, self.link_relpath)

    def render(self):
        with open(self.src_abspath, "rt") as fd:
            template_body = fd.read()
        try:
            template = self.jinja2.from_string(template_body)
        except:
            log.exception("%s: cannot load template", self.src_relpath)
            raise IgnorePage
        body = template.render(
            page=self,
        )
        return {
            self.dst_relpath: RenderedString(body),
        }

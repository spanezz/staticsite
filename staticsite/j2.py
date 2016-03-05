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
        basename = os.path.basename(relpath)
        dirname = os.path.dirname(relpath)
        dst_basename = basename.replace(".j2", "")
        dst_relpath = os.path.join(dirname, dst_basename)

        if dst_basename == "index.html":
            linkpath = dirname
        else:
            linkpath = os.path.join(dirname, dst_basename)

        super().__init__(
            site=site,
            root_abspath=root_abspath,
            src_relpath=relpath,
            src_linkpath=linkpath,
            dst_relpath=dst_relpath,
            dst_link=os.path.join(settings.SITE_ROOT, linkpath))

        self.jinja2 = j2env.jinja2

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

# coding: utf-8

from .core import Page, RenderedString
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

    def try_create(self, site, relpath):
        basename = os.path.basename(relpath)
        if ".j2." not in basename:
            return None
        dirname = os.path.dirname(relpath)
        try:
            return J2Page(self, site, os.path.join(dirname, basename.replace(".j2", "")), template_relpath=relpath)
        except IgnorePage:
            return None


class J2Page(Page):
    TYPE = "jinja2"

    def __init__(self, j2env, site, relpath, template_relpath):
        super().__init__(site, relpath)
        self.jinja2 = j2env.jinja2
        self.template_relpath = template_relpath
        try:
            self.template = self.jinja2.get_template(self.template_relpath)
        except:
            log.exception("%s: cannot load template %s", self.src_relpath, self.template_relpath)
            raise IgnorePage

    def render(self):
        body = self.template.render(
            page=self,
            **self.meta,
        )
        return {
            self.dst_relpath: RenderedString(body),
        }

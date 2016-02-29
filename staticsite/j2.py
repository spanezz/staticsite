# coding: utf-8

from .core import Page
import os
import re
from collections import defaultdict
import logging

log = logging.getLogger()


class J2Pages:
    def __init__(self, j2env):
        self.jinja2 = j2env

    def try_create(self, site, relpath):
        basename = os.path.basename(relpath)
        if ".j2." not in basename:
            return None
        dirname = os.path.dirname(relpath)
        return J2Page(self, site, os.path.join(dirname, basename.replace(".j2", "")), template_relpath=relpath)


class J2Page(Page):
    TYPE = "jinja2"

    def __init__(self, j2env, site, relpath, template_relpath):
        super().__init__(site, relpath)
        self.jinja2 = j2env.jinja2
        self.template_relpath = template_relpath

    def write(self, writer):
        try:
            template = self.jinja2.get_template(self.template_relpath)
        except:
            log.exception("%s: cannot load template %s", self.src_relpath, self.template_relpath)
            return
        body = template.render(
            **self.meta,
        )
        dst = writer.output_abspath(self.dst_relpath)
        with open(dst, "wt") as out:
            out.write(body)

    def check(self, checker):
        try:
            template = self.jinja2.get_template(self.template_relpath)
        except:
            log.exception("%s: cannot load template %s", self.src_relpath, self.template_relpath)

# coding: utf-8

from .core import Page
import os
import re
from collections import defaultdict
import logging

log = logging.getLogger()

re_metaname = re.compile("^__(?P<name>.+)__(?P<ext>\..+)$")

class J2Page(Page):
    TYPE = "jinja2"

    def __init__(self, site, relpath, template_relpath):
        super().__init__(site, relpath)
        self.template_relpath = template_relpath

    def transform(self):
        basename = os.path.basename(self.src_relpath)
        mo = re_metaname.match(basename)
        if not mo:
            return

        metaname = mo.group("name")
        ext = mo.group("ext")

        # We are a metapage: remove ourself from the site and add instead the
        # resolved versions
        dirname = os.path.dirname(self.src_relpath)
        del self.site.pages[self.src_relpath]

        # Resolve the file name into a taxonomy
        elements = self.site.taxonomies.get(metaname, None)
        if elements is None:
            log.warn("%s: taxonomy %s not found", self.src_relpath, metaname)
            return

        # Get the pages for each taxonomy value
        pages = defaultdict(list)
        for p in self.site.pages.values():
            vals = p.meta.get(metaname, None)
            if vals is None: continue
            for v in vals:
                pages[v].append(p)

        for e in elements:
            slug = self.site.slugify(e)
            new_basename = slug + ext
            new_page = J2Page(self.site, os.path.join(dirname, new_basename), self.template_relpath)
            new_page.meta["taxonomy_name"] = metaname
            new_page.meta["taxonomy_item"] = e
            new_page.meta["taxonomy_slug"] = slug
            new_page.meta["pages"] = sorted(pages.get(e, ()), key=lambda x:x.meta.get("date", None), reverse=True)
            self.site.pages[new_page.src_relpath] = new_page


    @classmethod
    def try_create(cls, site, relpath):
        basename = os.path.basename(relpath)
        if ".j2." not in basename:
            return None
        dirname = os.path.dirname(relpath)
        return cls(site, os.path.join(dirname, basename.replace(".j2", "")), template_relpath=relpath)


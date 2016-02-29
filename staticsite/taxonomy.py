# coding: utf-8

from .core import Page
import os
import re
from collections import defaultdict
import logging

log = logging.getLogger()

class TaxonomyPages:
    def __init__(self, j2env):
        self.jinja2 = j2env

    def try_create(self, site, relpath):
        if not relpath.endswith(".taxonomy"): return None
        return TaxonomyPage(self, site, relpath[:-9])


class TaxonomyPage(Page):
    TYPE = "taxonomy"
    ANALYZE_PASS = 2

    def __init__(self, j2env, site, relpath):
        super().__init__(site, relpath)
        self.jinja2 = j2env.jinja2

        # Taxonomy name (e.g. "tags")
        self.name = os.path.basename(self.src_relpath)

        # Map all possible values for this taxonomy to the pages that reference
        # them
        self.values = defaultdict(list)

        self.template_index = None
        self.template_feed = None
        self.template_archive = None

        self.meta["output_index"] = "{slug}/"
        self.meta["output_feed"] = "{slug}/feed.rss"
        self.meta["output_archive"] = "{slug}/archive.html"

        ## Generate taxonomies from configuration
        #self.taxonomies = {}
        #for name, info in settings.TAXONOMIES.items():
        #    info["name"] = name
        #    output_dir = info.get("output_dir", None)
        #    if output_dir is not None:
        #        info["output_dir"] = self.enforce_relpath(output_dir)
        #    self.taxonomies[name] = Taxonomy(**info)

    def link_value(self, output_item, value):
        dest = self.meta[output_item].format(slug=self.site.slugify(value))
        if dest.endswith("/"):
            dest += "index.html"
        return "/" + os.path.join(self.dst_relpath, dest)

    def load_template_from_meta(self, name):
        template_name = self.meta.get(name, None)
        if template_name is None: return None
        try:
            return self.jinja2.get_template(template_name)
        except:
            log.exception("%s: cannot load %s %s", self.src_relpath, name, template_name)
            return None

    def read_metadata(self):
        from .utils import parse_front_matter

        # Read taxonomy information
        src = os.path.join(self.site.root, self.src_relpath + ".taxonomy")
        with open(src, "rt") as fd:
            lines = [x.rstrip() for x in fd]
        try:
            self.meta.update(**parse_front_matter(lines))
        except:
            log.exception("%s.taxonomy: cannot parse taxonomy information", self.src_relpath)

        # Instantiate jinja2 templates
        self.template_index = self.load_template_from_meta("template_index")
        self.template_feed = self.load_template_from_meta("template_feed")
        self.template_archive = self.load_template_from_meta("template_archive")

        # Extend jinja2 with a function to link to elements of this taxonomy
        single_name = self.meta.get("item_name", self.name)
        self.jinja2.globals["url_for_" + single_name] = lambda x: self.link_value("output_index", x)
        self.jinja2.globals["url_for_" + single_name + "_feed"] = lambda x: self.link_value("output_feed", x)
        self.jinja2.globals["url_for_" + single_name + "_archive"] = lambda x: self.link_value("output_archive", x)

        # Collect the pages annotated with this taxonomy
        for page in self.site.pages.values():
            if page.ANALYZE_PASS > 1 : continue
            vals = page.meta.get(self.name, None)
            if vals is None: continue
            for v in vals:
                self.values[v].append(page)

    def write(self, writer):
        single_name = self.meta.get("item_name", self.name)

        for val, pages in self.values.items():
            val_slug = self.site.slugify(val)

            for type in ("index", "feed", "archive"):
                template = getattr(self, "template_" + type, None)
                if template is None: continue

                dest = self.meta["output_" + type].format(slug=val_slug)
                if dest.endswith("/"):
                    dest += "index.html"

                kwargs = {
                    "page": self,
                    single_name: val,
                    "slug": val_slug,
                    "pages": sorted(pages, key=lambda x:x.meta["date"], reverse=True),
                }
                kwargs.update(**self.meta)
                body = template.render(**kwargs)
                dst = writer.output_abspath(os.path.join(self.dst_relpath, dest))
                with open(dst, "wt") as out:
                    out.write(body)

from staticsite.page import Page
from staticsite.rendered import RenderedString
from staticsite.feature import Feature
import os
import jinja2
import logging

log = logging.getLogger()


class TaxonomyPages(Feature):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.taxonomies = []
        self.j2_globals["taxonomies"] = self.jinja2_taxonomies

    def try_load_page(self, root_abspath, relpath):
        if not relpath.endswith(".taxonomy"):
            return None
        page = TaxonomyPage(self.site, root_abspath, relpath)
        self.taxonomies.append(page)
        return page

    def build_test_page(self, name, **kw) -> Page:
        page = TestTaxonomyPage(self.site, root_abspath="/", relpath=name + ".taxonomy")
        page.meta.update(**kw)
        self.taxonomies.append(page)
        return page

    def finalize(self):
        # Assign pages to their taxonomies
        for page in self.site.pages.values():
            for taxonomy in self.taxonomies:
                vals = page.meta.get(taxonomy.name, None)
                if not vals:
                    continue
                taxonomy.add_page(page, vals)

        for taxonomy in self.taxonomies:
            taxonomy.finalize()

    def jinja2_taxonomies(self):
        return self.taxonomies


class TaxonomyItem:
    def __init__(self, page, name):
        self.page = page
        self.name = name
        self.slug = self.page.site.slugify(name)
        self.pages = []

    def __str__(self):
        return self.name


class TaxonomyPage(Page):
    TYPE = "taxonomy"
    ANALYZE_PASS = 2
    RENDER_PREFERRED_ORDER = 2

    def __init__(self, site, root_abspath, relpath):
        linkpath = os.path.splitext(relpath)[0]

        super().__init__(
            site=site,
            root_abspath=root_abspath,
            src_relpath=relpath,
            src_linkpath=linkpath,
            dst_relpath=linkpath,
            dst_link=os.path.join(site.settings.SITE_ROOT, linkpath))

        # Taxonomy name (e.g. "tags")
        self.name = os.path.basename(linkpath)

        # Map all possible values for this taxonomy to the pages that reference
        # them
        self.items = {}

        self.template_index = None
        self.template_item = None
        self.template_feed = None
        self.template_archive = None

        self.meta["output_index"] = ""
        self.meta["output_item"] = "{slug}/"
        self.meta["output_rss"] = "{slug}/index.rss"
        self.meta["output_atom"] = "{slug}/index.atom"
        self.meta["output_archive"] = "{slug}/archive.html"

        # # Generate taxonomies from configuration
        # self.taxonomies = {}
        # for name, info in self.site.settings.TAXONOMIES.items():
        #     info["name"] = name
        #     output_dir = info.get("output_dir", None)
        #     if output_dir is not None:
        #         info["output_dir"] = self.enforce_relpath(output_dir)
        #     self.taxonomies[name] = Taxonomy(**info)

        # Read taxonomy information
        self._read_taxonomy_description()

    def _read_taxonomy_description(self):
        """
        Parse the taxonomy file to read its description
        """
        from staticsite.utils import parse_front_matter
        src = self.src_abspath
        with open(src, "rt") as fd:
            lines = [x.rstrip() for x in fd]
        try:
            style, meta = parse_front_matter(lines)
            self.meta.update(**meta)
        except Exception:
            log.exception("%s.taxonomy: cannot parse taxonomy information", self.src_relpath)

    def link_value(self, context, output_item, value):
        if isinstance(value, str):
            item = self.items.get(value, None)
        else:
            item = value

        if item is None:
            log.warn("%s+%s: %s not found in taxonomy %s", context.parent["page"], context.name, value, self.name)
            return ""
        dest = self.meta[output_item].format(slug=item.slug)
        return os.path.join(self.site.settings.SITE_ROOT, self.dst_relpath, dest)

    @jinja2.contextfunction
    def link_index(self, context):
        dest = self.meta["output_index"]
        if not dest:
            return os.path.join(self.site.settings.SITE_ROOT, self.dst_relpath)
        else:
            return os.path.join(self.site.settings.SITE_ROOT, self.dst_relpath, dest)

    @jinja2.contextfunction
    def link_item(self, context, value):
        return self.link_value(context, "output_item", value)

    @jinja2.contextfunction
    def link_rss(self, context, value):
        return self.link_value(context, "output_rss", value)

    @jinja2.contextfunction
    def link_atom(self, context, value):
        return self.link_value(context, "output_atom", value)

    @jinja2.contextfunction
    def link_archive(self, context, value):
        return self.link_value(context, "output_archive", value)

    def load_template_from_meta(self, name):
        template_name = self.meta.get(name, None)
        if template_name is None:
            return None
        try:
            return self.site.theme.jinja2.get_template(template_name)
        except Exception:
            log.exception("%s: cannot load %s %s", self.src_relpath, name, template_name)
            return None

    def finalize(self):
        single_name = self.meta.get("item_name", self.name)

        # Instantiate jinja2 templates
        self.template_index = self.load_template_from_meta("template_" + self.name)
        self.template_item = self.load_template_from_meta("template_" + single_name)
        self.template_rss = self.load_template_from_meta("template_rss")
        self.template_atom = self.load_template_from_meta("template_atom")
        self.template_archive = self.load_template_from_meta("template_archive")

        # Extend jinja2 with a function to link to elements of this taxonomy
        self.site.theme.jinja2.globals["url_for_" + self.name] = self.link_index
        self.site.theme.jinja2.globals["url_for_" + single_name] = self.link_item
        self.site.theme.jinja2.globals["url_for_" + single_name + "_rss"] = self.link_rss
        self.site.theme.jinja2.globals["url_for_" + single_name + "_atom"] = self.link_atom
        self.site.theme.jinja2.globals["url_for_" + single_name + "_archive"] = self.link_archive

    def add_page(self, page, elements):
        """
        Add a page to this taxonomy. Elements is a sequence of elements for
        this taxonomy.
        """
        for v in elements:
            item = self.items.get(v, None)
            if item is None:
                item = TaxonomyItem(self, v)
                self.items[v] = item
            item.pages.append(page)

    def render(self):
        res = {}

        single_name = self.meta.get("item_name", self.name)

        if self.template_index is not None:
            dest = os.path.join(self.dst_relpath, self.meta["output_index"])
            if dest.endswith("/"):
                dest += "index.html"
            kwargs = {
                "page": self,
                self.name: sorted(self.items.values(), key=lambda x: x.name),
            }
            kwargs.update(**self.meta)
            body = self.template_index.render(**kwargs)
            res[dest] = RenderedString(body)

        for item in self.items.values():
            for type in ("item", "rss", "atom", "archive"):
                template = getattr(self, "template_" + type, None)
                if template is None:
                    continue

                dest = self.meta["output_" + type].format(slug=item.slug)
                if dest.endswith("/"):
                    dest += "index.html"

                kwargs = {
                    "page": self,
                    single_name: item,
                    "pages": sorted(item.pages, key=lambda x: x.meta["date"], reverse=True),
                }
                kwargs.update(**self.meta)
                body = template.render(**kwargs)
                res[os.path.join(self.dst_relpath, dest)] = RenderedString(body)

        return res

    def target_relpaths(self):
        res = []

        if self.template_index is not None:
            dest = os.path.join(self.dst_relpath, self.meta["output_index"])
            if dest.endswith("/"):
                dest += "index.html"
            res.append(dest)

        for item in self.items.values():
            for type in ("item", "rss", "atom", "archive"):
                template = getattr(self, "template_" + type, None)
                if template is None:
                    continue

                dest = self.meta["output_" + type].format(slug=item.slug)
                if dest.endswith("/"):
                    dest += "index.html"

                res.append(os.path.join(self.dst_relpath, dest))

        return res


class TestTaxonomyPage(TaxonomyPage):
    def _read_taxonomy_description(self):
        pass

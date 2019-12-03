from __future__ import annotations
from typing import List, Dict, Iterable
from staticsite.page import Page
from staticsite.render import RenderedString
from staticsite.feature import Feature
from staticsite.file import File, Dir
import functools
import os
import logging

log = logging.getLogger()


class TaxonomyFeature(Feature):
    """
    Tag pages using one or more taxonomies.

    See doc/taxonomies.md for details.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        # All TaxonomyPages found
        self.taxonomies: Dict[str, TaxonomyPage] = {}

        self.j2_globals["taxonomies"] = self.jinja2_taxonomies
        self.j2_globals["taxonomy"] = self.jinja2_taxonomy

    def load_dir(self, sitedir: Dir) -> List[Page]:
        # meta = sitedir.meta_features.get("j2")
        # if meta is None:
        #     meta = {}

        taken = []
        pages = []
        for fname, src in sitedir.files.items():
            if not fname.endswith(".taxonomy"):
                continue

            if os.path.basename(src.relpath)[:-9] not in self.site.settings.TAXONOMIES:
                log.warn("%s: ignoring taxonomy not listed in TAXONOMIES settings", src.relpath)
                continue

            page = TaxonomyPage(self.site, src, meta=sitedir.meta_file(fname))
            self.taxonomies[page.name] = page
            taken.append(fname)
            pages.append(page)

        for fname in taken:
            del sitedir.files[fname]

        return pages

    def build_test_page(self, name: str, **kw) -> Page:
        page = TestTaxonomyPage(self.site, File(relpath=name + ".taxonomy", root="/", abspath="/" + name + ".taxonomy"))
        page.meta.update(**kw)
        self.taxonomies[page.name] = page
        return page

    def jinja2_taxonomies(self) -> Iterable["TaxonomyPage"]:
        return self.taxonomies.values()

    def jinja2_taxonomy(self, name) -> "TaxonomyPage":
        return self.taxonomies.get(name)

    def finalize(self):
        # Scan all pages for taxonomies.

        # Do it here instead of hooking into self.for_metadata and do this at
        # page load time, so that we are sure that all .taxonomy files have
        # been loaded
        for page in list(self.site.pages.values()):
            for name, taxonomy in self.taxonomies.items():
                categories = page.meta.get(name)
                if categories is None:
                    continue
                taxonomy.add_page(page, categories)

        # Warn of taxonomies configured in settings.TAXONOMIES but not mounted
        # with a <name>.taxonomy
        for name in self.site.settings.TAXONOMIES:
            if name not in self.taxonomies:
                log.warn("Taxonomy %s defined in settings, but no %s.taxonomy file found in site contents: ignoring it",
                         name, name)

        # Call finalize on all taxonomy pages, now that we fully populated them
        for taxonomy in self.taxonomies.values():
            taxonomy.finalize()


class TaxonomyPage(Page):
    """
    Root page for one taxonomy defined in the site
    """
    TYPE = "taxonomy"
    RENDER_PREFERRED_ORDER = 2

    def __init__(self, site, src, meta=None):
        linkpath = os.path.splitext(src.relpath)[0]

        super().__init__(
            site=site,
            src=src,
            src_linkpath=linkpath,
            dst_relpath=os.path.join(linkpath, "index.html"),
            dst_link=os.path.join(site.settings.SITE_ROOT, linkpath),
            meta=meta)

        # Taxonomy name (e.g. "tags")
        self.name = os.path.basename(linkpath)

        # Map all possible values for this taxonomy to the pages that reference
        # them
        self.categories: Dict[str, CategoryPage] = {}

        # Read taxonomy information
        self._read_taxonomy_description()

        # Template used to render this taxonomy
        self.template_tags = self.site.theme.jinja2.get_template(self.meta.get("template_tags", "tags.html"))

        # Template used to render each single category index
        self.template_tag = self.site.theme.jinja2.get_template(self.meta.get("template_tag", "tag.html"))

        # Template used to render the archive view of each single category index
        self.template_tag_archive = self.site.theme.jinja2.get_template(
                self.meta.get("template_archive", "tag-archive.html"))

        self.validate_meta()

    def _read_taxonomy_description(self):
        """
        Parse the taxonomy file to read its description
        """
        from staticsite.utils import parse_front_matter
        with open(self.src.abspath, "rt") as fd:
            lines = [x.rstrip() for x in fd]
        try:
            style, meta = parse_front_matter(lines)
            self.meta.update(**meta)
        except Exception:
            log.exception("%s: cannot parse taxonomy information", self.src.relpath)

    def add_page(self, page, categories):
        """
        Add a page to this taxonomy.

        :arg categories: a sequence of categories that the page declares for
                         this taxonomy
        """
        category_pages = []
        for v in categories:
            category_page = self.categories.get(v, None)
            if category_page is None:
                category_page = CategoryPage(self, v)
                self.categories[v] = category_page
                self.site.pages[category_page.src_linkpath] = category_page
                self.site.pages[category_page.archive.src_linkpath] = category_page.archive
            category_pages.append(category_page)
            category_page.add_page(page)

        # Replace tag names in page.meta with CategoryPage pages
        category_pages.sort(key=lambda p: p.name)
        page.meta[self.name] = category_pages

    def __getitem__(self, name):
        return self.categories[name]

    def finalize(self):
        self.categories = {k: v for k, v in sorted(self.categories.items())}
        for category in self.categories.values():
            category.finalize()

    def render(self):
        res = {}

        if self.template_tags is not None:
            body = self.render_template(self.template_tags)
            res[self.dst_relpath] = RenderedString(body)

        return res


@functools.total_ordering
class CategoryPage(Page):
    """
    Index page showing all the pages tagged with a given taxonomy item
    """
    TYPE = "category"
    RENDER_PREFERRED_ORDER = 2

    def __init__(self, taxonomy, name):
        relpath = os.path.join(taxonomy.src_linkpath, name)
        super().__init__(
            site=taxonomy.site,
            src=File(relpath=relpath),
            src_linkpath=relpath,
            dst_relpath=os.path.join(relpath, "index.html"),
            dst_link=os.path.join(taxonomy.site.settings.SITE_ROOT, relpath))
        # Category name
        self.name = name
        # Taxonomy we belong to
        self.taxonomy: TaxonomyPage = taxonomy
        # Pages that have this category
        self.pages: List[Page] = []

        self.meta.setdefault("title", name)
        self.meta.setdefault("date", taxonomy.meta["date"])
        self.validate_meta()

        # Archive page
        self.archive = CategoryArchivePage(self)

    def __lt__(self, o):
        o_taxonomy = getattr(o, "taxonomy", None)
        if o_taxonomy is None:
            return NotImplemented

        o_name = getattr(o, "name", None)
        if o_name is None:
            return NotImplemented

        return (self.taxonomy.name, self.name) < (o_taxonomy.name, o_name)

    def __eq__(self, o):
        o_taxonomy = getattr(o, "taxonomy", None)
        if o_taxonomy is None:
            return NotImplemented

        o_name = getattr(o, "name", None)
        if o_name is None:
            return NotImplemented

        return (self.taxonomy.name, self.name) == (o_taxonomy.name, o_name)

    def add_page(self, page):
        """
        Add a page to this category.
        """
        # Our date is the maximum of all pages
        page_date = page.meta["date"]
        if page_date > self.meta["date"]:
            self.meta["date"] = page_date

        self.pages.append(page)

    def finalize(self):
        self.pages.sort(key=lambda x: x.meta["date"], reverse=True)
        self.archive.finalize()

    def render(self):
        return {
            self.dst_relpath: RenderedString(self.render_template(self.taxonomy.template_tag)),
        }


class CategoryArchivePage(Page):
    """
    Index page showing the archive page for a CategoryPage
    """
    TYPE = "category_archive"
    RENDER_PREFERRED_ORDER = 2

    def __init__(self, category_page):
        relpath = os.path.join(category_page.src_linkpath, "archive")
        super().__init__(
            site=category_page.site,
            src=File(relpath=relpath),
            src_linkpath=relpath,
            dst_relpath=os.path.join(relpath, "index.html"),
            dst_link=os.path.join(category_page.site.settings.SITE_ROOT, relpath))

        # Category name
        self.name = category_page.name

        # Taxonomy we belong to
        self.taxonomy: TaxonomyPage = category_page.taxonomy

        # Category we belong to
        self.category: CategoryPage = category_page

        self.meta.setdefault("title", category_page.meta["title"])
        self.meta.setdefault("date", category_page.meta["date"])
        self.validate_meta()

    def finalize(self):
        self.meta["date"] = self.category.meta["date"]
        self.pages = self.category.pages

    def render(self):
        return {
            self.dst_relpath: RenderedString(self.render_template(self.taxonomy.template_tag_archive)),
        }


class TestTaxonomyPage(TaxonomyPage):
    def _read_taxonomy_description(self):
        pass


FEATURES = {
    "tags": TaxonomyFeature,
}

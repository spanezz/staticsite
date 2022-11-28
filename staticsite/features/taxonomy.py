from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Iterable, Optional
from staticsite import Page
from staticsite.feature import Feature
from staticsite.metadata import Metadata
from collections import defaultdict
import heapq
import functools
import os
import logging

if TYPE_CHECKING:
    from staticsite import file, scan
    from staticsite.typing import Meta

log = logging.getLogger("taxonomy")


class TaxonomyFeature(Feature):
    """
    Tag pages using one or more taxonomies.

    See doc/reference/taxonomies.md for details.
    """
    RUN_BEFORE = ["autogenerated_pages", "dirs"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.known_taxonomies = set()

        # All TaxonomyPages found
        self.taxonomies: Dict[str, TaxonomyPage] = {}

        self.j2_globals["taxonomies"] = self.jinja2_taxonomies
        self.j2_globals["taxonomy"] = self.jinja2_taxonomy

    def register_taxonomy_name(self, name):
        self.known_taxonomies.add(name)
        self.site.structure.tracked_metadata.add(name)
        # Note that if we want to make the tags inheritable, we need to
        # interface with 'rst' (or 'rst' to interface with us) because rst
        # needs to know which metadata items are taxonomies in order to parse
        # them.
        # Instead of making tags inheritable from normal metadata, we can offer
        # them to be added by 'files' or 'dirs' directives.
        self.site.register_metadata(Metadata(name, structure=True, doc=f"""
List of categories for the `{name}` taxonomy.

Setting this as a simple string is the same as setting it as a list of one
element.
"""))

    def load_dir_meta(self, sourcedir: scan.SourceDir, files: dict[str, file.File]):
        for fname in files.keys():
            if not fname.endswith(".taxonomy"):
                continue
            self.register_taxonomy_name(fname[:-9])

    def load_dir(self, sourcedir: scan.SourceDir, files: dict[str, tuple[Meta, file.File]]) -> List[Page]:
        taken: List[str] = []
        pages: List[Page] = []
        for fname, (meta, src) in files.items():
            if not fname.endswith(".taxonomy"):
                continue
            taken.append(fname)

            name = fname[:-9]

            meta["site_path"] = os.path.join(sourcedir.meta["site_path"], name)

            try:
                fm_meta = self.load_file_meta(sourcedir, src, fname)
            except Exception:
                log.exception("%s: cannot parse taxonomy information", src.relpath)
                continue
            meta.update(fm_meta)

            page = TaxonomyPage(self.site, src=src, meta=meta, name=name, dir=sourcedir)
            self.taxonomies[page.name] = page
            pages.append(page)

        for fname in taken:
            del files[fname]

        return pages

    def load_file_meta(self, sourcedir: scan.SourceDir, src: file.File, fname: str):
        """
        Parse the taxonomy file to read its description
        """
        from staticsite.utils import front_matter
        with sourcedir.open(fname, src, "rt") as fd:
            fmt, meta = front_matter.read_whole(fd)
        if meta is None:
            meta = {}
        return meta

    def jinja2_taxonomies(self) -> Iterable["TaxonomyPage"]:
        return self.taxonomies.values()

    def jinja2_taxonomy(self, name) -> Optional["TaxonomyPage"]:
        return self.taxonomies.get(name)

    def finalize(self):
        # Call finalize on all taxonomy pages, to populate them by scanning
        # site pages
        for taxonomy in self.taxonomies.values():
            taxonomy.finalize()


class TaxonomyPage(Page):
    """
    Root page for one taxonomy defined in the site
    """
    TYPE = "taxonomy"

    def __init__(self, *args, name: str, **kw):
        super().__init__(*args, **kw)

        self.meta["build_path"] = os.path.join(self.meta["site_path"], "index.html")
        self.meta.setdefault("template", "taxonomy.html")
        self.meta.setdefault("nav_title", name.capitalize())

        # Taxonomy name (e.g. "tags")
        self.name = name

        # Map all possible values for this taxonomy to the pages that reference
        # them
        self.categories: Dict[str, CategoryPage] = {}

        # Metadata for category pages
        self.category_meta = self.meta.get("category", {})
        self.category_meta.setdefault("template", "blog.html")
        self.category_meta.setdefault("template_title", "{{page.name}}")

        synd = self.category_meta.get("syndication")
        if synd is None or synd is True:
            self.category_meta["syndication"] = synd = {}
        elif synd is False:
            synd = None

        if synd is not None:
            synd.setdefault("add_to", False)

            archive = synd.get("archive")
            if archive is None or archive is True:
                synd["archive"] = archive = {}
            elif archive is False:
                archive = None

            if archive is not None:
                archive.setdefault("template_title", "{{page.created_from.name}} archive")
                self.site.theme.precompile_metadata_templates(archive)

        self.site.theme.precompile_metadata_templates(self.category_meta)

    def to_dict(self):
        from staticsite.utils import dump_meta
        res = super().to_dict()
        res["name"] = self.name
        res["categories"] = dump_meta(self.categories)
        res["category_meta"] = dump_meta(self.category_meta)
        return res

    def __getitem__(self, name):
        return self.categories[name]

    def top_categories(self, count=10):
        """
        Return the ``count`` categories with the most pages
        """
        return heapq.nlargest(count, self.categories.values(), key=lambda c: len(c.meta["pages"]))

    def most_recent(self, count=10):
        """
        Return the ``count`` categories with the most recent date
        """
        return heapq.nlargest(count, self.categories.values(), key=lambda c: c.meta["date"])

    def finalize(self):
        # Group pages by category
        by_category = defaultdict(list)
        for page in self.site.structure.pages_by_metadata[self.name]:
            categories = page.meta.get(self.name)
            if not categories:
                continue
            # Make sure page.meta.$category is a list
            if isinstance(categories, str):
                categories = page.meta[self.name] = (categories,)
            # File the page in its category lists
            for category in categories:
                by_category[category].append(page)

        # Create category pages
        for category, pages in by_category.items():
            # Sort pages by date, used by series sequencing
            pages.sort(key=lambda p: p.meta["date"])

            # Create category page
            category_meta = dict(self.category_meta)
            category_meta["taxonomy"] = self
            category_meta["pages"] = pages
            category_meta["date"] = pages[-1].meta["date"]
            category_meta["site_path"] = os.path.join(self.meta["site_path"], category)

            category_page = CategoryPage.create_from(self, meta=category_meta, name=category)
            self.categories[category] = category_page
            self.site.add_page(category_page)

        # Replace category names with category pages in each categorized page
        for page in self.site.structure.pages_by_metadata[self.name]:
            categories = page.meta.get(self.name)
            if not categories:
                continue
            page.meta[self.name] = [self.categories[c] for c in categories]

        # Sort categories dict by category name
        self.categories = {k: v for k, v in sorted(self.categories.items())}

        # Set self.meta.pages to the sorted list of categories
        self.meta["pages"] = list(self.categories.values())


@functools.total_ordering
class CategoryPage(Page):
    """
    Index page showing all the pages tagged with a given taxonomy item
    """
    TYPE = "category"

    def __init__(self, *args, name: str = None, **kw):
        super().__init__(*args, **kw)
        self.meta["build_path"] = os.path.join(self.meta["site_path"], "index.html")
        # Category name
        self.name = name
        # Index of each page in the category sequence
        self.page_index: Dict[Page, int] = {page: idx for idx, page in enumerate(self.meta["pages"])}

    def to_dict(self):
        res = super().to_dict()
        res["name"] = self.name
        return res

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

    def series_info(self):
        """
        Return a dict describing this category as a series
        """
        # Compute a series title for this page.
        # Look for the last defined series title, defaulting to the title of
        # the first page in the series.
        pages = self.meta["pages"]
        series_title = pages[0].meta["title"]
        return {
            # Array with all the pages in the series
            "pages": pages,
            "length": len(pages),
            "first": pages[0],
            "last": pages[-1],
            "title": series_title,
        }

    def sequence(self, page):
        idx = self.page_index.get(page)
        if idx is None:
            return None

        # Compute a series title for this page.
        # Look for the last defined series title, defaulting to the title of
        # the first page in the series.
        pages = self.meta["pages"]
        series_title = pages[0].meta["title"]
        for p in pages:
            title = p.meta.get("series_title")
            if title is not None:
                series_title = title
            if p == page:
                break

        return {
            # Array with all the pages in the series
            "pages": pages,
            # Assign series_prev and series_next metadata elements to pages
            "index": idx + 1,
            "length": len(pages),
            "first": pages[0],
            "last": pages[-1],
            "prev": pages[idx - 1] if idx > 0 else None,
            "next": pages[idx + 1] if idx < len(pages) - 1 else None,
            "title": series_title,
        }


class TestTaxonomyPage(TaxonomyPage):
    def _read_taxonomy_description(self):
        pass


FEATURES = {
    "taxonomy": TaxonomyFeature,
}

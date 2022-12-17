from __future__ import annotations

import functools
import heapq
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional

from staticsite import fields
from staticsite.feature import Feature, TrackedFieldMixin
from staticsite.features.syndication import Syndication
from staticsite.node import Path
from staticsite.page import SourcePage, AutoPage, Page, ChangeExtent
from staticsite.utils import front_matter

if TYPE_CHECKING:
    from staticsite import file, fstree
    from staticsite.node import Node

log = logging.getLogger("taxonomy")


class Taxonomy:
    """
    Definition of a taxonomy for the site
    """
    def __init__(self, *, name: str, src: file.File, **kw):
        self.name = name
        self.src = src
        self.index: Optional[Page] = None
        # Metadata for the taxonomy index page
        self.index_meta: dict[str, Any] = {"taxonomy": self}
        # Metadata for the category pages
        self.category_meta: dict[str, Any] = {}
        # Metadata for the archive pages
        self.archive_meta: dict[str, Any] = {}
        # Category pages by category name
        self.category_pages: dict[str, Page] = {}

    def update_meta(
            self,
            category: Optional[dict[str, Any]] = None,
            archive: Optional[dict[str, Any]] = None,
            **kw):
        """
        Add information from a parsed taxonomy file
        """
        self.index_meta.update(kw)

        # Metadata for category pages
        if category is not None:
            self.category_meta.update(category)
        self.category_meta.setdefault("template_title", "{{page.name}}")

        # Metadata for archive pages
        if archive is not None:
            self.archive_meta.update(archive)

    def create_index(self, node: Node) -> TaxonomyPage:
        """
        Create the index page for this taxonomy
        """
        self.index = node.create_source_page(
            page_cls=TaxonomyPage,
            src=self.src,
            name=self.name,
            directory_index=True,
            path=Path((self.name,)),
            **self.index_meta)
        return self.index

    def create_category_page(self, name: str, pages: List[Page]) -> CategoryPage:
        """
        Generate the page for one category in this taxonomy
        """
        # Sort pages by date, used by series sequencing
        pages.sort(key=lambda p: p.date)

        # Create category page
        category_meta = dict(self.category_meta)
        category_meta["pages"] = pages
        category_meta["date"] = pages[-1].date

        # Syndication
        if (syndication_value := category_meta.pop("syndication", None)) is not None:
            syndication = Syndication.clean_value(None, syndication_value)
        else:
            syndication = Syndication(None)

        if syndication is not None:
            category_meta["syndication"] = syndication
            category_meta["syndication"].archive.update(self.archive_meta)

        # Don't auto-add feeds for the tag syndication pages
        syndication.add_to = False

        # TODO: archive

        # if archive is not None:
        #     self.archive_meta.update(archive)
        #     elif archive is False:
        #         archive = None

        #     if archive is not None:
        #         archive.setdefault("template_title", "{{meta.created_from.name}} archive")

        return self.index.node.create_auto_page(
            created_from=self.index,
            page_cls=CategoryPage,
            name=name,
            path=Path((name,)),
            **category_meta)

    def generate_pages(self):
        self.category_meta["taxonomy"] = self.index

        # Group pages by category
        by_category: dict[str, list[Page]] = defaultdict(list)
        for page in self.index.site.features.pages_by_metadata[self.name]:
            categories = getattr(page, self.name, None)
            if not categories:
                continue
            # Make sure page.meta.$category is a list
            # TODO: move to field validator
            if isinstance(categories, str):
                categories = (categories,)
                setattr(page, self.name, categories)
            # File the page in its category lists
            for category in categories:
                by_category[category].append(page)

        # Create category pages
        for category, pages in by_category.items():
            self.category_pages[category] = self.create_category_page(category, pages)

        # Replace category names with category pages in each categorized page
        for page in self.index.site.features.pages_by_metadata[self.name]:
            if not (categories := getattr(page, self.name, None)):
                continue
            setattr(page, self.name, [self.category_pages[c] for c in categories])

        # Sort categories dict by category name
        self.category_pages = {k: v for k, v in sorted(self.category_pages.items())}

        # Set self.meta.pages to the sorted list of categories
        self.index.pages = list(self.category_pages.values())


class TaxonomyField(TrackedFieldMixin, fields.Field):
    tracked_by = "taxonomy"
    # TODO: make this validate as string lists


class BaseTaxonomyPageMixin(metaclass=fields.FieldsMetaclass):
    series_title = fields.Field(doc="""
        Series title from this page onwards.

        If this page is part of a series, and it defines `series_title`, then
        the series title will be changed to this, from this page onwards, but
        not for the previous pages
    """)


class TaxonomyPageMixin(BaseTaxonomyPageMixin):
    """
    Base class for dynamically generated taxonomy page mixins
    """
    # This is empty to begin with, to serve as a base for TaxonomyMixins
    # dynamically generated when taxonomies are found


class TaxonomyFeature(Feature):
    """
    Tag pages using one or more taxonomies.

    See doc/reference/taxonomies.md for details.
    """
    RUN_BEFORE = ["autogenerated_pages"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.known_taxonomies = set()

        # All TaxonomyPages found
        self.taxonomies: dict[str, Taxonomy] = {}

        self.j2_globals["taxonomies"] = self.jinja2_taxonomies
        self.j2_globals["taxonomy"] = self.jinja2_taxonomy

    def register_taxonomy(self, name, src: file.File):
        # Note that if we want to make the tags inheritable, we need to
        # interface with 'rst' (or 'rst' to interface with us) because rst
        # needs to know which metadata items are taxonomies in order to parse
        # them.
        # Instead of making tags inheritable from normal metadata, we can offer
        # them to be added by 'files' or 'dirs' directives.
        self.page_mixins.append(type("TaxonomyMixin", (TaxonomyPageMixin,), {
            name: TaxonomyField(structure=True, default=(), doc=f"""
                List of categories for the `{name}` taxonomy.

                Setting this as a simple string is the same as setting it as a list of one
                element.
            """)}))
        self.known_taxonomies.add(name)
        self.site.features.add_tracked_metadata(name)
        self.taxonomies[name] = Taxonomy(name=name, src=src)

    def load_dir_meta(self, directory: fstree.Tree) -> Optional[dict[str, Any]]:
        for fname, src in directory.files.items():
            if not fname.endswith(".taxonomy"):
                continue
            self.register_taxonomy(fname[:-9], src)

    def load_dir(
            self,
            node: Node,
            directory: fstree.Tree,
            files: dict[str, tuple[dict[str, Any], file.File]]) -> list[Page]:
        taken: List[str] = []
        pages: List[Page] = []
        for fname, (kwargs, src) in files.items():
            if not fname.endswith(".taxonomy"):
                continue
            taken.append(fname)

            taxonomy = self.taxonomies[fname[:-9]]

            try:
                fm_meta = self.load_file_meta(directory, fname)
            except Exception:
                log.exception("%s: cannot parse taxonomy information", src.relpath)
                continue
            kwargs.update(fm_meta)

            taxonomy.update_meta(**kwargs)
            pages.append(taxonomy.create_index(node))

        for fname in taken:
            del files[fname]

        return pages

    def load_file_meta(self, directory: fstree.Tree, fname: str) -> dict[str, Any]:
        """
        Parse the taxonomy file to read its description
        """
        with directory.open(fname, "rt") as fd:
            fmt, meta = front_matter.read_whole(fd)
        if meta is None:
            meta = {}
        return meta

    def jinja2_taxonomies(self) -> Iterable["TaxonomyPage"]:
        return [t.index for t in self.taxonomies.values()]

    def jinja2_taxonomy(self, name) -> Optional["TaxonomyPage"]:
        if (taxonomy := self.taxonomies.get(name)):
            return taxonomy.index
        return None

    def generate(self):
        # Call analyze on all taxonomy pages, to populate them by scanning
        # site pages
        for taxonomy in self.taxonomies.values():
            taxonomy.generate_pages()


class TaxonomyPage(SourcePage):
    """
    Root page for one taxonomy defined in the site
    """
    TYPE = "taxonomy"
    TEMPLATE = "taxonomy.html"

    taxonomy = fields.Field(doc="Structured taxonomy information")

    def __init__(self, *args, name: str, **kw):
        kw.setdefault("nav_title", name.capitalize())
        super().__init__(*args, **kw)

        # Taxonomy name (e.g. "tags")
        self.name = name

    @property
    def categories(self):
        """
        Map all possible values for this taxonomy to the pages that reference
        them
        """
        return self.taxonomy.category_pages

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
        return heapq.nlargest(count, self.categories.values(), key=lambda c: len(c.pages))

    def most_recent(self, count=10):
        """
        Return the ``count`` categories with the most recent date
        """
        return heapq.nlargest(count, self.categories.values(), key=lambda c: c.date)

    def _compute_footprint(self) -> dict[str, Any]:
        res = super()._compute_footprint()
        # Map categories to list of page relpaths
        taxonomy = {}
        for name, category in self.taxonomy.category_pages.items():
            taxonomy[name] = [page.src.relpath for page in category.pages if getattr(page, "src", None)]
        res["taxonomy"] = taxonomy
        return res

    def _compute_change_extent(self) -> ChangeExtent:
        if (old := self.footprint.get("taxonomy")) is None:
            return ChangeExtent.ALL

        # Check if categories have been added or removed
        if old.keys() != self.taxonomy.category_pages.keys():
            return ChangeExtent.ALL

        # Aggregate change extends from category pages
        if self.taxonomy.category_pages:
            return max(page.change_extent for page in self.taxonomy.category_pages.values())
        else:
            return ChangeExtent.UNCHANGED


@functools.total_ordering
class CategoryPage(AutoPage):
    """
    Index page showing all the pages tagged with a given taxonomy item
    """
    TYPE = "category"
    TEMPLATE = "blog.html"

    taxonomy = fields.Field(doc="Page that defined this taxonomy")
    name = fields.Field(doc="Name of the category shown in this page")

    def __init__(self, *args, name: str = None, **kw):
        super().__init__(*args, **kw)
        # Category name
        self.name = name
        # Index of each page in the category sequence
        self.page_index: Dict[Page, int] = {page: idx for idx, page in enumerate(self.pages)}

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

    def __hash__(self):
        return hash((self.taxonomy.name, self.name))

    @functools.cached_property
    def series_info(self):
        """
        Return a dict describing this category as a series
        """
        # Compute a series title for this page.
        # Look for the last defined series title, defaulting to the title of
        # the first page in the series.
        pages = self.pages
        series_title = pages[0].series_title or pages[0].title
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
        pages = self.pages
        series_title = pages[0].title
        for p in pages:
            if (title := p.series_title) is not None:
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

    def _compute_change_extent(self) -> ChangeExtent:
        # No previous footprint
        if self.created_from.old_footprint is None:
            return ChangeExtent.ALL
        if (old_footprint := self.created_from.old_footprint.get("taxonomy")) is None:
            return ChangeExtent.ALL

        # This category did not previously exist
        if (old_sources_list := old_footprint.get(self.name)) is None:
            return ChangeExtent.ALL
        else:
            old_sources = set(old_sources_list)

        sources = {page.src.relpath for page in self.pages if getattr(page, "src", None)}
        if sources != old_sources:
            # If any page added or removed this category, we rebuild
            return ChangeExtent.ALL

        if self.pages:
            return max(p.change_extent for p in self.pages)
        else:
            return ChangeExtent.ALL


class TestTaxonomyPage(TaxonomyPage):
    def _read_taxonomy_description(self):
        pass


FEATURES = {
    "taxonomy": TaxonomyFeature,
}

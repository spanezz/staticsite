from __future__ import annotations

import functools
import heapq
import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any, Union, cast

from staticsite import fields
from staticsite.feature import Feature, TrackedField
from staticsite.features.syndication import Syndication
from staticsite.page import (
    AutoPage,
    ChangeExtent,
    ConstPageField,
    Page,
    SourcePage,
    TemplatePage,
)
from staticsite.utils import front_matter

if TYPE_CHECKING:
    from staticsite import file, fstree
    from staticsite.source_node import SourcePageNode

log = logging.getLogger("taxonomy")


class Taxonomy:
    """
    Definition of a taxonomy for the site
    """

    def __init__(self, *, name: str, src: file.File, **kw: Any):
        self.name = name
        self.src = src
        self.index: TaxonomyPage | None = None
        # Pages that declare categories in this taxonomy
        self.pages: set[Page] = set()
        # Metadata for the taxonomy index page
        self.index_meta: dict[str, Any] = {"taxonomy": self}
        # Metadata for the category pages
        self.category_meta: dict[str, Any] = {}
        # Metadata for the archive pages
        self.archive_meta: dict[str, Any] = {}
        # Category pages by category name
        self.category_pages: dict[str, CategoryPage] = {}

    def update_meta(
        self,
        category: dict[str, Any] | None = None,
        archive: dict[str, Any] | None = None,
        **kw: Any,
    ) -> None:
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

    def create_index(self, node: SourcePageNode) -> TaxonomyPage | None:
        """
        Create the index page for this taxonomy
        """
        self.index = node.create_source_page_as_path(
            page_cls=TaxonomyPage, src=self.src, name=self.name, **self.index_meta
        )
        return self.index

    def create_category_page(self, name: str, pages: list[Page]) -> CategoryPage | None:
        """
        Generate the page for one category in this taxonomy
        """
        if self.index is None:
            raise RuntimeError(
                "Taxonomy.create_category_page called without an index page"
            )
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

        return self.index.node.create_auto_page_as_path(
            created_from=self.index, page_cls=CategoryPage, name=name, **category_meta
        )

    def generate_pages(self) -> None:
        if self.index is None:
            raise RuntimeError("Taxonomy.generate_pages called without an index page")
        self.category_meta["taxonomy"] = self.index

        # Group pages by category
        by_category: dict[str, list[Page]] = defaultdict(list)
        for page in self.pages:
            categories = getattr(page, self.name, None)
            if not categories:
                continue
            # File the page in its category lists
            for category in categories:
                by_category[category].append(page)

        # Create category pages
        for category, pages in by_category.items():
            if (cpage := self.create_category_page(category, pages)) is not None:
                self.category_pages[category] = cpage

        # Replace category names with category pages in each categorized page
        for page in self.pages:
            if not (categories := getattr(page, self.name, None)):
                continue
            setattr(
                page,
                self.name,
                [
                    p
                    for c in categories
                    if (p := self.category_pages.get(c)) is not None
                ],
            )

        # Sort categories dict by category name
        self.category_pages = {k: v for k, v in sorted(self.category_pages.items())}

        # Set self.meta.pages to the sorted list of categories
        self.index.pages = list(self.category_pages.values())


class TaxonomyField(TrackedField[Page, Union[list[str], list[Page]]]):
    tracked_by = "taxonomy"

    def _clean(
        self, page: Page, value: None | str | list[str] | list[Page]
    ) -> list[str] | list[Page]:
        if not value:
            return cast(list[Page], [])
        elif isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            return value
        else:
            raise ValueError(
                f"{value!r} is not a string, a list of strings, or a list of Page objects"
            )


class BaseTaxonomyPageMixin(Page):
    series_title = fields.Str["BaseTaxonomyPageMixin"](
        doc="""
        Series title from this page onwards.

        If this page is part of a series, and it defines `series_title`, then
        the series title will be changed to this, from this page onwards, but
        not for the previous pages
    """
    )


class TaxonomyPageMixin(BaseTaxonomyPageMixin):
    """
    Base class for dynamically generated taxonomy page mixins
    """

    # This is empty to begin with, to serve as a base for TaxonomyMixins
    # dynamically generated when taxonomies are found


class TaxonomyFeature(Feature):
    """
    Tag pages using one or more taxonomies.

    Files with a `.taxonomy` extension represent where that taxonomy will appear in
    the built site.

    For example, `dir/tags.taxonomy` will become `dir/tags/…` in the built site,
    and contain an index of all categories in the taxonomy, and for each category
    an index page, an archive page, and rss and atom feeds.

    **Added in 1.3**: Removed again the need to list in [`TAXONOMIES` settings](../settings.md)
    the taxonomies used in the site.

    **Added in 1.2**: Any taxonomy you use needs to be explicitly listed in
    settings as a `TAXONOMIES` list of taxonomy names. staticsite prints a warning
    if a `.taxonomy` file is found that is not listed in `TAXONOMIES`.

    The `.taxonomy` file will be a yaml, json, or toml file, like in
    [markdown](../pages/markdown.md) front matter.

    The relevant fields in a taxonomy file are:

    * `title`, `description`: used for the taxonomy index page
    * `category`: metadata for the page generated for each category in the taxonomy
    * `archive`: metadata for the page generated for each category archive

    * **changed in 1.2**: `template_tags`: use `template` instead
    * **changed in 1.2**: `template_tag`: use `category/template` instead
    * **changed in 1.2**: `template_archive`: use `archive/template` instead
    * **Removed in 1.2**: `output_dir` is now ignored, and the taxonomy pages will
      be put in a directory with the same name as the file, without extension
    * **Changed in 1.2**: `item_name` in a `.taxonomy` file does not have a special
      meaning anymore, and templates can still find it in the taxonomy page
      metadata
    * **Added in 1.2**: page.meta["tags"] or other taxonomy names gets substituted,
      from a list of strings, to a list of pages for the taxonomy index, which can
      be used to generate links and iterate subpages in templates without the need
      of specialised functions.
    * **Removed in 1.2**: `series_tags` is now ignored: every category can be used
      to build a series

    Example:

    ```yaml
    ---
    # In staticsite, a taxonomy is a group of attributes like categories or tags.
    #
    # Like in Hugo, you can have as many taxonomies as you want. See
    # https://gohugo.io/taxonomies/overview/ for a general introduction to
    # taxonomies.
    #
    # This file describes the taxonomy for "tags". The name of the taxonomy is
    # taken from the file name.
    #
    # The format of the file is the same that is used for the front matter of
    # posts, again same as in Hugo: https://gohugo.io/content/front-matter/

    # Template for rendering the taxonomy index. Here, it's the page that shows the
    # list of tags
    template: taxonomy.html

    category:
       # Template for rendering the page for one tag. Here, it's the page that shows
       # the latest pages tagged with the tag
       template: blog.html
       # Title used in category pages
       template_title: "Latest posts for tag <strong>{{page.name}}</strong>"
       # Description used in category pages
       template_description: "Most recent posts with tag <strong>{{page.name}}</strong>"

       syndication:
         add_to: no
         archive:
           # Template for rendering the archive page for one tag. Here, it's the page that
           # links to all the pages tagged with the tag
           template_title: "Archive of posts for tag <strong>{{page.name}}</strong>"
           template_description: "Archive of all posts with tag <strong>{{page.name}}</strong>"
    ```


    ### Jinja2 templates

    Each taxonomy defines extra `url_for_*` functions. For example, given a *tags*
    taxonomy with *tag* as singular name:

     * `taxonomies()`: list of all taxonomy index pages, ordered by name
     * `taxonomy(name)`: taxonomy index page for the given taxonomy
     * **Removed in 1.2**: `url_for_tags()`: links to the taxonomy index.
     * **Removed in 1.2**: `url_for_tag(tag)`: use `url_for(category)`
     * **Removed in 1.2**: `url_for_tag_archive(tag)`: use `url_for(category.archive)`
     * **Removed in 1.2**: `url_for_tag_rss(tag)`: see [the syndication feature](syndication.md)
     * **Removed in 1.2**: `url_for_tag_atom(tag)`: see [the syndication feature](syndication.md)

    ## Series of posts

    Any category of any taxonomy collects an ordered list of posts, that can be
    used to generate interlinked series of pages.

    All posts in a category are ordered by date (see [page metadata](markdown.md)).

    Given a [category page](taxonomies.md), the `.sequence(page)` method locates
    the page in the sequence of pages in that category, returning a dictionary
    with these values:

    * `index`: position of this page in the series (starts from 1)
    * `length`: number of pages in the series
    * `first`: first page in the series
    * `last`: last page in the series
    * `prev`: previous page in the series, if available
    * `next`: next page in the series, if available
    * `title`: title for the series

    This example template renders the position of the page in the series, choosing
    as a series the first category of the page in a taxonomy called `series`:

    ```jinja2
    {% with place = page.meta.series[0].sequence(page) %}
    {{place.title}} {{place.index}}/{{place.length}}
    {% endwith %}
    ```

    ### Series title

    The series title is, by default, the title of the first page in the series.

    If a page defines a `series_title` header, then it becomes the series title
    from that page onwards. It is possible to redefine the series title during a
    series, like for example a "My trip" series that later becomes "My trip:
    Italy", "My trip: France", "My trip: Spain", and so on.

    ## Multiple series for a page

    A page is part of one series for each category of each taxonomy it has.
    Templates need to choose which categories are relevant for use in generating
    series navigation links.
    """

    RUN_BEFORE = ["syndication"]

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        # All TaxonomyPages found
        self.taxonomies: dict[str, Taxonomy] = {}
        self.page_bases: list[type[Page]] = []

        self.j2_globals["taxonomies"] = self.jinja2_taxonomies
        self.j2_globals["taxonomy"] = self.jinja2_taxonomy

    def get_page_bases(self, page_cls: type[Page]) -> Sequence[type[Page]]:
        return self.page_bases

    def get_used_page_types(self) -> list[type[Page]]:
        return [TaxonomyPage, CategoryPage]

    def track_field(self, field: fields.Field[Any, Any], obj: Page, value: Any) -> None:
        self.taxonomies[field.name].pages.add(obj)

    def register_taxonomy(self, name: str, src: file.File) -> None:
        # Note that if we want to make the tags inheritable, we need to
        # interface with 'rst' (or 'rst' to interface with us) because rst
        # needs to know which metadata items are taxonomies in order to parse
        # them.
        # Instead of making tags inheritable from normal metadata, we can offer
        # them to be added by 'files' or 'dirs' directives.
        self.page_bases.append(
            type(
                "TaxonomyMixin",
                (TaxonomyPageMixin,),
                {
                    name: TaxonomyField(
                        structure=True,
                        default=(),
                        doc=f"""
                List of categories for the `{name}` taxonomy.

                Setting this as a simple string is the same as setting it as a list of one
                element.
            """,
                    )
                },
            )
        )
        self.taxonomies[name] = Taxonomy(name=name, src=src)

    def load_dir_meta(self, directory: fstree.Tree) -> dict[str, Any] | None:
        for fname, src in directory.files.items():
            if not fname.endswith(".taxonomy"):
                continue
            self.register_taxonomy(fname[:-9], src)
        return None

    def load_dir(
        self,
        node: SourcePageNode,
        directory: fstree.Tree,
        files: dict[str, tuple[dict[str, Any], file.File]],
    ) -> list[Page]:
        taken: list[str] = []
        pages: list[Page] = []
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
            if (page := taxonomy.create_index(node)) is None:
                continue
            pages.append(page)

        for fname in taken:
            del files[fname]

        return pages

    def load_file_meta(self, directory: fstree.Tree, fname: str) -> dict[str, Any]:
        """
        Parse the taxonomy file to read its description
        """
        with directory.open(fname, "rt") as fd:
            fmt, meta = front_matter.read_whole(fd)
        return meta

    def jinja2_taxonomies(self) -> Iterable[TaxonomyPage]:
        return [t.index for t in self.taxonomies.values() if t.index is not None]

    def jinja2_taxonomy(self, name: str) -> TaxonomyPage | None:
        if taxonomy := self.taxonomies.get(name):
            return taxonomy.index
        return None

    def generate(self) -> None:
        # Call analyze on all taxonomy pages, to populate them by scanning
        # site pages
        for taxonomy in self.taxonomies.values():
            taxonomy.generate_pages()


class TaxonomyPage(TemplatePage, SourcePage):
    """
    Root page for one taxonomy defined in the site

    Pages generated by the taxonomy feature have these extra attributes:

    * `name`: the taxonomy name (e.g. "tags")
    * `categories`: dict mapping category names to category index pages. In
      templates, the dict is sorted by category name.
    * The page can be indexed by category name, returning the corresponding
      category index page.
    """

    TYPE = "taxonomy"
    TEMPLATE = "taxonomy.html"

    taxonomy = fields.ConstTypeField["TaxonomyPage", Taxonomy](
        cls=Taxonomy, doc="Structured taxonomy information"
    )

    def __init__(self, *args: Any, node: SourcePageNode, **kw: Any):
        kw.setdefault("nav_title", node.name.capitalize())
        super().__init__(*args, node=node, **kw)

        # Taxonomy name (e.g. "tags")
        self.name = self.node.name

    @property
    def categories(self) -> dict[str, CategoryPage]:
        """
        Map all possible values for this taxonomy to the pages that reference
        them
        """
        return self.taxonomy.category_pages

    def to_dict(self) -> dict[str, Any]:
        from staticsite.utils import dump_meta

        res = super().to_dict()
        res["name"] = self.name
        res["categories"] = dump_meta(self.categories)
        return res

    def __getitem__(self, name: str) -> CategoryPage:
        return self.categories[name]

    def top_categories(self, count: int = 10) -> list[CategoryPage]:
        """
        Return the ``count`` categories with the most pages
        """
        return heapq.nlargest(
            count,
            self.categories.values(),
            key=lambda c: len(c.pages) if c.pages else 0,
        )

    def most_recent(self, count: int = 10) -> list[CategoryPage]:
        """
        Return the ``count`` categories with the most recent date
        """
        return heapq.nlargest(count, self.categories.values(), key=lambda c: c.date)

    def _compute_footprint(self) -> dict[str, Any]:
        res = super()._compute_footprint()
        # Map categories to list of page relpaths
        taxonomy: dict[str, list[str]] = {}
        for name, category in self.taxonomy.category_pages.items():
            if not category.pages:
                taxonomy[name] = []
            else:
                taxonomy[name] = [
                    page.src.relpath
                    for page in category.pages
                    if isinstance(page, SourcePage)
                ]
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
            return max(
                page.change_extent for page in self.taxonomy.category_pages.values()
            )
        else:
            return ChangeExtent.UNCHANGED


@functools.total_ordering
class CategoryPage(TemplatePage, AutoPage):
    """
    Index page showing all the pages tagged with a given taxonomy item

    Pages generated by the taxonomy feature have these extra attributes:

    * `page.name`: the category name
    * `page.meta.pages`: the pages that have this category
    * `page.meta.taxonomy`: the taxonomy index page for this category
    * `page.meta.archive`: the archive page for this category

    **Category archive**:

    This is created automatically by the [syndication](../features/syndication.md) feature.

    You can refer to the category page from its archive page, using
    `page.created_from`.
    """

    TYPE = "category"
    TEMPLATE = "blog.html"

    taxonomy = ConstPageField["CategoryPage", TaxonomyPage](
        cls=TaxonomyPage, doc="Page that defined this taxonomy"
    )
    name = fields.Str["CategoryPage"](doc="Name of the category shown in this page")

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        # Category name
        self.name = self.node.name
        # Index of each page in the category sequence
        self.page_index: dict[Page, int] = (
            {page: idx for idx, page in enumerate(self.pages)} if self.pages else {}
        )

    def to_dict(self) -> dict[str, Any]:
        res = super().to_dict()
        res["name"] = self.name
        return res

    def __lt__(self, o: Any) -> bool:
        o_taxonomy = getattr(o, "taxonomy", None)
        if o_taxonomy is None:
            return NotImplemented

        o_name = getattr(o, "name", None)
        if o_name is None:
            return NotImplemented

        return (self.taxonomy.name, self.name) < (o_taxonomy.name, o_name)

    def __eq__(self, o: Any) -> bool:
        o_taxonomy = getattr(o, "taxonomy", None)
        if o_taxonomy is None:
            return NotImplemented

        o_name = getattr(o, "name", None)
        if o_name is None:
            return NotImplemented

        return (self.taxonomy.name, self.name) == (o_taxonomy.name, o_name)

    def __hash__(self) -> int:
        return hash((self.taxonomy.name, self.name))

    @functools.cached_property
    def series_info(self) -> dict[str, Any] | None:
        """
        Return a dict describing this category as a series
        """
        # Compute a series title for this page.
        # Look for the last defined series title, defaulting to the title of
        # the first page in the series.
        if (pages := self.pages) is None:
            return None
        series_title = (
            cast(BaseTaxonomyPageMixin, pages[0]).series_title or pages[0].title
        )
        return {
            # Array with all the pages in the series
            "pages": pages,
            "length": len(pages),
            "first": pages[0],
            "last": pages[-1],
            "title": series_title,
        }

    def sequence(self, page: Page) -> dict[str, Any] | None:
        idx = self.page_index.get(page)
        if idx is None:
            return None

        # Compute a series title for this page.
        # Look for the last defined series title, defaulting to the title of
        # the first page in the series.
        if (pages := self.pages) is None:
            return None
        series_title = pages[0].title
        for p in pages:
            if (title := cast(BaseTaxonomyPageMixin, p).series_title) is not None:
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
        if self.created_from is None:
            raise AssertionError(f"CategoryPage {self!r} found with empty created_from")

        index = cast(TaxonomyPage, self.created_from)

        # No previous footprint
        if index.old_footprint is None:
            return ChangeExtent.ALL
        if (old_footprint := index.old_footprint.get("taxonomy")) is None:
            return ChangeExtent.ALL

        # This category did not previously exist
        if (old_sources_list := old_footprint.get(self.name)) is None:
            return ChangeExtent.ALL
        else:
            old_sources = set(old_sources_list)

        sources = (
            {page.src.relpath for page in self.pages if isinstance(page, SourcePage)}
            if self.pages
            else {}
        )
        if sources != old_sources:
            # If any page added or removed this category, we rebuild
            return ChangeExtent.ALL

        if self.pages:
            return max(p.change_extent for p in self.pages)
        else:
            return ChangeExtent.ALL


class TestTaxonomyPage(TaxonomyPage):
    def _read_taxonomy_description(self) -> None:
        pass


FEATURES = {
    "taxonomy": TaxonomyFeature,
}

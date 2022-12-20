from __future__ import annotations

import datetime
import logging
import os
from typing import Any, List, Optional, Sequence, Union, Type

import jinja2

from staticsite import fields
from staticsite.feature import Feature, TrackedField, PageTrackingMixin
from staticsite.node import Path
from staticsite.page import AutoPage, Page, PageNotFoundError, ChangeExtent, TemplatePage
from staticsite.utils import arrange

log = logging.getLogger("syndication")


class Syndication:
    """
    Syndication information for a group of pages
    """
    def __init__(
            self,
            index: Page, *,
            title: Optional[str] = None,
            description: Optional[str] = None,
            template_title: Optional[str] = None,
            template_description: Optional[str] = None,
            add_to: Union[bool, str, None] = True,
            archive: Union[bool, dict[str, Any]] = True):
        # Default metadata for syndication pages
        self.default_meta: dict[str, Any] = {}
        if title is not None:
            self.default_meta["title"] = title
        if description is not None:
            self.default_meta["description"] = description
        if template_title is not None:
            self.default_meta["template_title"] = template_title
        if template_description is not None:
            self.default_meta["template_description"] = template_description

        # Page that defined the syndication
        self.index: Page = index

        # Pages that get syndicated
        self.pages: List[Page] = []

        # Pages to which we add feed information
        #
        # If True: defaults to self.pages.
        #
        # If a string: expanded as a page filter
        self.add_to = add_to

        # Describe if and how to build an archive for this syndication
        self.archive: Optional[dict[str, Any]]
        if archive is False:
            self.archive = None
        elif archive is True:
            self.archive = {}
        elif isinstance(archive, dict):
            self.archive = archive
        else:
            raise ValueError(f"{archive!r} is not a valid value for a syndication.archive field")

        # RSS feed page
        self.rss_page: Optional[RSSPage] = None

        # Atom feed page
        self.atom_page: Optional[AtomPage] = None

        # Archive page
        self.archive_page: Optional[AtomPage] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "pages": self.pages,
            "add_to": self.add_to,
            "archive": self.archive,
            "rss_page": self.rss_page,
            "atom_page": self.atom_page,
            "archive_page": self.archive_page,
        }

    def generate(self):
        """
        Create autogenerated pages
        """
        # Generate RSS and Atom feeds
        self.make_feeds()

        # Make archive pages
        self.make_archive()

    def make_feeds(self):
        """
        Build RSS and Atom feeds
        """
        if "title" not in self.default_meta and "template_title" not in self.default_meta:
            self.default_meta["title"] = self.index.title

        if ("description" not in self.default_meta and "template_description"
                not in self.default_meta and self.index.description):
            self.default_meta["description"] = self.index.description

        page_name, ext = os.path.splitext(self.index.dst)

        kwargs = self.default_meta
        kwargs["pages"] = self.pages
        kwargs["index"] = self.index

        # RSS feed
        rss_page = self.index.node.create_auto_page(
                created_from=self.index,
                page_cls=RSSPage,
                dst=f"{page_name}.{RSSPage.TYPE}",
                **kwargs)
        self.rss_page = rss_page
        log.debug("%s: adding syndication page for %s", rss_page, self.index)
        # print(f"  rss_page {rss_page.meta=!r}")

        # Atom feed
        atom_page = self.index.node.create_auto_page(
                created_from=self.index,
                page_cls=AtomPage,
                dst=f"{page_name}.{AtomPage.TYPE}",
                **kwargs)
        self.atom_page = atom_page
        log.debug("%s: adding syndication page for %s", atom_page, self.index)

        self.index.add_related("rss_feed", self.rss_page)
        self.index.add_related("atom_feed", self.atom_page)

    def make_archive(self):
        """
        Build archive pages
        """
        if self.archive is None:
            return

        self.archive["pages"] = self.pages
        self.archive["index"] = self.index
        self.archive_page = self.index.node.create_auto_page(
                created_from=self.index,
                page_cls=ArchivePage,
                path=Path(("archive",)),
                **self.archive,
                )
        if self.archive_page is not None:
            self.archive_page.add_related("rss_feed", self.rss_page)
            self.archive_page.add_related("atom_feed", self.atom_page)

    def crossreference(self):
        """
        Cross-correlate generated pages
        """
        # Build the final list of the pages covered by the syndication
        self.fill_pages()

        # Add feed pages according to syndication.add_to
        self.process_add_to()

    def fill_pages(self):
        """
        Given a list of pages to potentially syndicate, filter them by their
        syndicated header, and sort by syndication date.
        """
        draft_mode = self.index.site.settings.DRAFT_MODE
        for page in self.index.pages or ():
            if not page.syndicated:
                continue
            if not draft_mode and page.syndication_date > page.site.generation_time:
                continue
            self.pages.append(page)
        self.pages.sort(key=lambda p: p.syndication_date, reverse=True)

        # Compute dates for generated pages
        if self.pages:
            max_date = max(p.date for p in self.pages)
            if self.rss_page is not None:
                self.rss_page.date = max_date
            if self.atom_page is not None:
                self.atom_page.date = max_date
            if self.archive_page is not None:
                self.archive_page.date = max_date

    def process_add_to(self):
        """
        Add a link to the syndication to the pages listed in add_to
        """
        add_to = self.add_to
        if add_to is False or add_to in ("no", "false", 0):
            pass
        elif add_to is True:
            for dest in self.pages:
                dest.add_related("rss_feed", self.rss_page)
                dest.add_related("atom_feed", self.atom_page)
        else:
            for dest in self.index.find_pages(**add_to):
                dest.add_related("rss_feed", self.rss_page)
                dest.add_related("atom_feed", self.atom_page)

    @classmethod
    def clean_value(self, page: Page, value: Any) -> Optional[Syndication]:
        """
        Instantiate a Syndication object from a Page field
        """
        if value is True:
            return Syndication(page)
        elif value is False:
            return None
        elif isinstance(value, Syndication):
            value.index = page
            return value
        elif isinstance(value, str):
            if value.lower() in ("yes", "true", "1"):
                return Syndication(page)
            else:
                return None
        elif isinstance(value, dict):
            return Syndication(page, **value)
        else:
            raise ValueError(f"{value!r} for `syndication` needs to be True or a dictionary of values")


class SyndicatedPageError(Exception):
    pass


class SyndicationField(TrackedField[Page, Optional[Syndication]]):
    """
    Defines syndication for the contents of this page.

    It is a structure which can contain normal metadata, plus:

    * `add_to`: chooses which pages will include a link to the RSS/Atom feeds.
      By default, the link is added to all syndicated pages. If this is `False`,
      then no feed is added to pages. If it is a dictionary, it selects pages in
      the site, similar to the `site_pages` function in [templates](templates.md).
      See [Selecting pages](page-filter.md) for details.
    * `archive`: if not false, an archive link will be generated next to the
      page. It can be set of a dictionary of metadata to be used as defaults for
      the generated archive page. It defaults to True.

    Any other metadata found in the structure are used when generating pages for
    the RSS/Atom feeds, so you can use `title`, `template_title`, `description`,
    and so on, to personalize the feeds.

    The pages that go in the feed are those listed in
    [`page.meta.pages`](doc/reference/pages.md), keeping into account the
    [`syndicated` and `syndication_date` page metadata](doc/reference/metadata.md).

    When rendering RSS/Atom feed pages, `page.meta.pages` is replaced with the list
    of syndicated pages, sorted with the most recent first.

    Setting `syndication` to true turns on syndication with all defaults,
    equivalent to:

    ```yaml
    syndication:
      add_to: yes
      archive:
        template: archive.html
    ```
    """
    tracked_by = "syndication"

    def _clean(self, page: Page, value: Any) -> Optional[Syndication]:
        return Syndication.clean_value(page, value)


class SyndicationDateField(fields.Date[Page]):
    def __get__(self, page: Page, type: Optional[Type] = None) -> datetime.datetime:
        if (date := page.__dict__.get(self.name)) is None:
            date = page.date
            page.__dict__[self.name] = date
        return date


class SyndicatedField(fields.Bool[Page]):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def __get__(self, page: Page, type: Optional[Type] = None) -> bool:
        if (value := page.__dict__.get(self.name)) is None:
            value = page.indexed
            page.__dict__[self.name] = value
            return value
        else:
            return value


class SyndicationPageMixin(Page):
    syndication = SyndicationField(structure=True)
    syndicated = SyndicatedField(doc="""
        Set to true if the page can be included in a syndication, else to false.

        If not set, it defaults to the value of `indexed`.
    """)
    syndication_date = SyndicationDateField(doc="""
        Syndication date for this page.

        This is the date that will appear in RSS and Atom feeds, and the page will not
        be syndicated before this date.

        Use this field to publish a date today but make it appear in
        syndication only at some point in the future.

        If a page is syndicated and `syndication_date` is missing, it defaults to `date`.
    """)
    # rss_page = fields.Field(doc="""
    #     Page with the RSS feed with posts for the syndication the page is in
    # """)
    # atom_page = fields.Field(doc="""
    #     Page with the Atom feed with posts for the syndication the page is in
    # """)
    # archive = fields.Field(doc="""
    #     Page with an archive of all posts for the syndication the page is in
    # """)


def _get_syndicated_pages(page: SyndicationPageMixin, limit: Optional[int] = None) -> List[Page]:
    """
    Get the sorted list of syndicated pages for a page
    """
    if (syndication := page.syndication) is not None:
        # syndication.pages is already sorted
        return syndication.pages[:limit]

    if (pages := page.pages) is None:
        raise SyndicatedPageError(f"page {page!r} has no `syndication.pages` or `pages` in metadata")
    return arrange(pages, "-syndication_date", limit=limit)


class SyndicationFeature(PageTrackingMixin, Feature):
    r"""
    Build syndication feeds for groups of pages.

    The Syndication feature implements generation of a [RSS](https://en.wikipedia.org/wiki/RSS)
    and [Atom](https://en.wikipedia.org/wiki/Atom_(Web_standard\)) feed for a page
    or group of pages.

    Add a `syndication` metadata to a page to declare it as the index for a group
    of page. RSS and Atom feeds will appear next to the page, containing pages
    selected in the `syndication` metadata.

    One page is used to define the syndication, using "syndication_*" tags.

    Use a data page without type to define a contentless syndication page

    ## Syndication metadata

    Example front page for a blog page:

    ```yaml
    ---
    pages: blog/*
    syndication: yes
    template: blog.html
    ---
    # My blog
    ```

    See [metadata documentation](metadata.md) for a reference on the `syndication`
    field.

    ## Syndication of taxonomies

    Each category page in each taxonomy automatically defines a syndication
    metadata equivalent to this:

    ```yaml
    syndication:
      add_to: no
    ```

    This would automatically generates RSS and Atom feeds with all pages in that
    category, but those feed links will only be added to the category page itself.

    You can use the `syndication` metadata in your taxonomy categories to customize
    titles and description in your categories feeds, like with any other page.


    ## Templates

    See the example templates for working `syndication.rss` and `syndication.atom`
    templates, that are used by the generated RSS and Atom pages.

    ### `syndicated_pages(page=None, limit=None)`

    Templates can use the `syndicated_pages` function to list syndicated pages for
    a page, sorted with the most recently syndicated first.

    `page` can be a page, a path to a page, or omitted, in which case the current
    page is used. `page` can also be a list of pages, which will be sorted by
    syndiaction date and sampled.

    `limit` is the number of pages to return, or, if omitted, all the pages are
    returned.
    """
    # syndication requires page.meta.pages prefilled by pages and taxonomy features
    RUN_AFTER = ["pages", "taxonomy"]
    RUN_BEFORE = ["autogenerated_pages"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site.features["rst"].yaml_tags.add("syndication")
        self.syndications = []
        self.j2_globals["syndicated_pages"] = self.jinja2_syndicated_pages

    def get_page_bases(self, page_cls: Type[Page]) -> Sequence[Type[Page]]:
        return (SyndicationPageMixin,)

    def get_used_page_types(self) -> list[Type[Page]]:
        return [RSSPage, AtomPage, ArchivePage]

    @jinja2.pass_context
    def jinja2_syndicated_pages(
            self, context, what: Union[str, Page, list[Page], None] = None, limit=None) -> list[Page]:
        """
        Get the list of pages to be syndicated
        """
        try:
            if what is None or isinstance(what, jinja2.Undefined):
                page = context.get("page")
                if page is None:
                    raise SyndicatedPageError(
                            "syndicated_pages called without a page argument, but page is not set in context")
                return _get_syndicated_pages(page, limit=limit)
            elif isinstance(what, str):
                src = context.get("page")
                if src is None:
                    raise SyndicatedPageError(
                            "syndicated_pages called without a page argument, but page is not set in context")

                try:
                    page = src.resolve_path(what)
                except PageNotFoundError as e:
                    log.warn("%s: %s", context.name, e)
                    return []

                return _get_syndicated_pages(page, limit=limit)
            elif isinstance(what, Page):
                return _get_syndicated_pages(what, limit=limit)
            else:
                return arrange(what, "-syndication_date", limit=limit)
        except SyndicatedPageError as e:
            log.warn("%s: %s", context.name, e)
            return []

    def generate(self):
        # Build syndications from pages with a 'syndication' metadata
        for page in self.tracked_pages:
            # The syndication header is the base for the feed pages's metadata,
            # and is added as 'syndication' to all the pages that get the feed
            # links
            if (syndication := page.syndication) is None:
                continue

            syndication.generate()

            self.syndications.append(syndication)

    def crossreference(self):
        for syndication in self.syndications:
            syndication.crossreference()


class SyndicationPage(TemplatePage, AutoPage):
    """
    Base class for syndication pages
    """
    index = fields.Field["SyndicationPage", SyndicationPageMixin](doc="""
        Page that defined the syndication for this feed
    """)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        if self.pages:
            self.date = max(p.date for p in self.pages)
        else:
            self.date = self.site.generation_time

    def _compute_change_extent(self) -> ChangeExtent:
        return self.created_from._compute_change_extent()


class RSSPage(SyndicationPage):
    """
    A RSS syndication page

    RSS and Atom pages have these extra properties:

    * `page.meta.template` defaults to `syndication.rss` or `syndication.atom`
      instead of `page.html`
    * `page.meta.date` is the most recent date of the pages in the feed
    * `page.meta.index` is the page defining the syndication
    * `page.meta.pages` is a list of all the pages included in the syndication
    """
    TYPE = "rss"
    TEMPLATE = "syndication.rss"


class AtomPage(SyndicationPage):
    """
    An Atom syndication page

    RSS and Atom pages have these extra properties:

    * `page.meta.template` defaults to `syndication.rss` or `syndication.atom`
      instead of `page.html`
    * `page.meta.date` is the most recent date of the pages in the feed
    * `page.meta.index` is the page defining the syndication
    * `page.meta.pages` is a list of all the pages included in the syndication
    """
    TYPE = "atom"
    TEMPLATE = "syndication.atom"


class ArchivePage(TemplatePage, AutoPage):
    """
    An archive page is automatically created for each syndication.

    * `page.meta.pages`: the pages in the archive
    * `page.created_from`: the page for which the archive page was created
    """

    index = fields.Field["ArchivePage", SyndicationPageMixin](doc="""
        Page that defined the syndication for this feed
    """)

    TYPE = "archive"
    TEMPLATE = "archive.html"

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.pages = self.created_from.pages

        if self.pages:
            self.date = max(p.date for p in self.pages)
        else:
            self.date = self.site.generation_time

        self.created_from.add_related("archive", self)

    def _compute_change_extent(self) -> ChangeExtent:
        return self.created_from._compute_change_extent()


FEATURES = {
    "syndication": SyndicationFeature,
}

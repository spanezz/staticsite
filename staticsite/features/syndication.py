from __future__ import annotations

import logging
import os
from typing import Any, List, Optional, Union

import jinja2

from staticsite import fields
from staticsite.feature import Feature
from staticsite.node import Path
from staticsite.page import Page, PageNotFoundError
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
        rss_page = self.index.node.create_page(
                created_from=self.index,
                page_cls=RSSPage,
                dst=f"{page_name}.{RSSPage.TYPE}",
                **kwargs)
        self.rss_page = rss_page
        log.debug("%s: adding syndication page for %s", rss_page, self.index)
        # print(f"  rss_page {rss_page.meta=!r}")

        # Atom feed
        atom_page = self.index.node.create_page(
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
        self.archive_page = self.index.node.create_page(
                created_from=self.index,
                page_cls=ArchivePage,
                path=Path(("archive",)),
                **self.archive,
                )
        self.archive_page.add_related("rss_feed", self.rss_page)
        self.archive_page.add_related("atom_feed", self.atom_page)

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
    def clean_value(self, page: Page, value: Any) -> Syndication:
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


class SyndicationField(fields.Field):
    def _clean(self, page: Page, value: Any) -> Syndication:
        return Syndication.clean_value(page, value)


class SyndicationPageMixin(metaclass=fields.FieldsMetaclass):
    syndication = SyndicationField(structure=True, doc="""
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
    """)
    syndicated = fields.Bool(doc="""
        Set to true if the page can be included in a syndication, else to false.

        If not set, it defaults to the value of `indexed`.
    """)
    syndication_date = fields.Date(doc="""
        Syndication date for this page.

        This is the date that will appear in RSS and Atom feeds, and the page will not
        be syndicated before this date.

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

    def validate(self):
        super().validate()

        # Make sure the syndicated field has a value
        if self.syndicated is None:
            # If not present, default to 'indexed'
            self.syndicated = self.indexed

        # Parse syndication_date to a date if provided.
        #
        # If page.meta.syndicate is true, it is always present, and if not set it
        # defaults to page.meta.date.
        if self.syndicated and self.syndication_date is None:
            self.syndication_date = self.date


def _get_syndicated_pages(page: Page, limit: Optional[int] = None) -> List[Page]:
    """
    Get the sorted list of syndicated pages for a page
    """
    if (syndication := page.syndication) is not None:
        # syndication.pages is already sorted
        return syndication.pages[:limit]

    if (pages := page.pages) is None:
        raise SyndicatedPageError(f"page {page!r} has no `syndication.pages` or `pages` in metadata")
    return arrange(pages, "-syndication_date", limit=limit)


class SyndicationFeature(Feature):
    """
    Build syndication feeds for groups of pages.

    One page is used to define the syndication, using "syndication_*" tags.

    Use a data page without type to define a contentless syndication page
    """
    # syndication requires page.meta.pages prefilled by pages and taxonomy features
    RUN_AFTER = ["pages", "taxonomy"]
    RUN_BEFORE = ["autogenerated_pages"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.page_mixins.append(SyndicationPageMixin)
        self.site.features["rst"].yaml_tags.add("syndication")
        self.site.features.add_tracked_metadata("syndication")
        self.syndications = []
        self.j2_globals["syndicated_pages"] = self.jinja2_syndicated_pages

    @jinja2.pass_context
    def jinja2_syndicated_pages(self, context, what: Union[str, Page, List[Page], None] = None, limit=None) -> bool:
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

    def analyze(self):
        # Build syndications from pages with a 'syndication' metadata
        for page in self.site.features.pages_by_metadata["syndication"]:
            # The syndication header is the base for the feed pages's metadata,
            # and is added as 'syndication' to all the pages that get the feed
            # links
            if (syndication := page.syndication) is None:
                continue

            # Build the final list of the pages covered by the syndication
            syndication.fill_pages()

            # Generate RSS and Atom feeds
            syndication.make_feeds()

            # Make archive pages
            syndication.make_archive()

            # Add feed pages according to syndication.add_to
            syndication.process_add_to()


class SyndicationPage(Page):
    """
    Base class for syndication pages
    """
    index = fields.Field(doc="""
        Page that defined the syndication for this feed
    """)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        if self.pages:
            self.date = max(p.date for p in self.pages)
        else:
            self.date = self.site.generation_time


class RSSPage(SyndicationPage):
    """
    A RSS syndication page
    """
    TYPE = "rss"
    TEMPLATE = "syndication.rss"


class AtomPage(SyndicationPage):
    """
    An Atom syndication page
    """
    TYPE = "atom"
    TEMPLATE = "syndication.atom"


class ArchivePage(Page):
    index = fields.Field(doc="""
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


FEATURES = {
    "syndication": SyndicationFeature,
}

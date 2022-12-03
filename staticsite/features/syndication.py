from __future__ import annotations

import logging
import os
from typing import Any, List, Optional, Union

import jinja2

from staticsite import structure
from staticsite.feature import Feature
from staticsite.metadata import Metadata
from staticsite.page import Page, PageNotFoundError
from staticsite.utils import arrange

log = logging.getLogger("syndication")


class MetadataSyndicated(Metadata):
    """
    Make sure the syndicated exists
    """
    def on_load(self, page: Page):
        val = page.meta.get(self.name)
        if val is None:
            # If not present, default to 'indexed'
            page.meta[self.name] = page.meta["indexed"]
        elif isinstance(val, str):
            page.meta[self.name] = val.lower() in ("yes", "true", "1")


class MetadataSyndicationDate(Metadata):
    """
    Parse to a date if provided.

    If page.meta.syndicate is true, it is always present, and if not set it
    defaults to page.meta.date.
    """
    def on_load(self, page: Page):
        date = page.meta.get(self.name)
        if date is None:
            if page.meta["syndicated"]:
                page.meta[self.name] = page.meta["date"]
        else:
            page.meta[self.name] = self.site.clean_date(date)


class SyndicatedPageError(Exception):
    pass


def _get_syndicated_pages(page: Page, limit: Optional[int] = None) -> List[Page]:
    """
    Get the sorted list of syndicated pages for a page
    """
    syndication = page.meta.get("syndication")
    if syndication is not None:
        pages = syndication.get("pages")
        if pages is not None:
            # meta.syndication.pages is already sorted
            if limit is None:
                return pages
            else:
                return pages[:limit]

    pages = page.meta.get("pages")
    if pages is None:
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
        self.site.features["rst"].yaml_tags.add("syndication")
        self.site.register_metadata(Metadata("syndication", structure=True, doc="""
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
"""))
        self.site.structure.add_tracked_metadata("syndication")

        self.site.register_metadata(MetadataSyndicated("syndicated", doc="""
Set to true if the page can be included in a syndication, else to false.

If not set, it defaults to the value of `indexed`.
"""))
        self.site.register_metadata(MetadataSyndicationDate("syndication_date", doc="""
Syndication date for this page.

This is the date that will appear in RSS and Atom feeds, and the page will not
be syndicated before this date.

If a page is syndicated and `syndication_date` is missing, it defaults to `date`.
"""))
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

    def prepare_syndication_list(self, pages) -> list[Page]:
        """
        Given a list of pages to potentially syndicate, filter them by their
        syndicated header, and sort by syndication date.
        """
        draft_mode = self.site.settings.DRAFT_MODE
        res = []
        for page in pages:
            if not page.meta["syndicated"]:
                continue
            if not draft_mode and page.meta["syndication_date"] > self.site.generation_time:
                continue
            res.append(page)
        res.sort(key=lambda p: p.meta["syndication_date"], reverse=True)
        return res

    def analyze(self):
        # Build syndications from pages with a 'syndication' metadata
        for page in self.site.structure.pages_by_metadata["syndication"]:
            # The syndication header is the base for the feed pages's metadata,
            # and is added as 'syndication' to all the pages that get the feed
            # links
            meta_dict = page.meta.get("syndication")
            # print(f"Syndication.analyze {page=!r} page.meta.syndication={meta_dict!r}")
            if meta_dict is None:
                continue
            elif meta_dict is True:
                meta_values = {}
            else:
                # Make a shallow copy to prevent undesired side effects if multiple
                # pages share the same syndication dict, as may be the case with
                # taxonomies
                meta_values = dict(meta_dict)
                # print(f"  initial base metadata for feeds {meta=!r}")

            # Add the syndication link to the index page
            page.meta["syndication"] = meta_values

            # Index page for the syndication
            meta_values["index"] = page

            # Pages involved in the syndication
            pages = page.meta.get("pages", [])
            meta_values["pages"] = self.prepare_syndication_list(pages)

            self.site.theme.precompile_metadata_templates(meta_values)

            # print(f"  final base metadata for feeds {meta=!r}")

            page_name, ext = os.path.splitext(page.build_node.name)

            # print(f"Syndication {page=!r}, {pages=}")

            # RSS feed
            rss_page = page.node.create_page(
                    created_from=page,
                    page_cls=RSSPage,
                    meta_values=meta_values,
                    dst=f"{page_name}.{RSSPage.TYPE}")
            rss_page.meta["rss_page"] = rss_page
            meta_values["rss_page"] = rss_page
            log.debug("%s: adding syndication page for %s", rss_page, page)
            # print(f"  rss_page {rss_page.meta=!r}")

            # Atom feed
            atom_page = page.node.create_page(
                    created_from=page,
                    page_cls=AtomPage,
                    meta_values=meta_values,
                    dst=f"{page_name}.{AtomPage.TYPE}")
            rss_page.meta["atom_page"] = atom_page
            atom_page.meta["atom_page"] = atom_page
            meta_values["atom_page"] = atom_page
            log.debug("%s: adding syndication page for %s", atom_page, page)

            # Archive page
            archive_meta_values: Optional[dict[str, Any]]
            if (val := meta_values.get("archive")) is False:
                archive_meta_values = None
            elif val is None or val is True:
                archive_meta_values = {}
            else:
                archive_meta_values = dict(val)

            if archive_meta_values is not None:
                archive_meta_values["pages"] = pages
                archive_meta_values["index"] = page
                archive_page = page.node.create_page(
                        created_from=page,
                        page_cls=ArchivePage,
                        meta_values=archive_meta_values,
                        path=structure.Path(("archive",)))
                archive_page.add_related("rss_feed", rss_page)
                archive_page.add_related("atom_feed", atom_page)

            page.add_related("rss_feed", rss_page)
            page.add_related("atom_feed", atom_page)

            # Add a link to the syndication to the pages listed in add_to
            add_to = meta_values.get("add_to", True)
            if add_to is False:
                pass
            elif add_to is True:
                for dest in pages:
                    dest.add_related("rss_feed", rss_page)
                    dest.add_related("atom_feed", atom_page)
            else:
                for dest in page.find_pages(**add_to):
                    dest.add_related("rss_feed", rss_page)
                    dest.add_related("atom_feed", atom_page)


class SyndicationPage(Page):
    """
    Base class for syndication pages
    """
    # Default template to use for this type of page
    TEMPLATE: str

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.meta.setdefault("template", self.TEMPLATE)
        if self.meta["pages"]:
            self.meta["date"] = max(p.meta["date"] for p in self.meta["pages"])
        else:
            self.meta["date"] = self.site.generation_time


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
    TYPE = "archive"

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.meta.setdefault("template", "archive.html")
        self.meta["pages"] = self.created_from.meta["pages"]

        if self.meta["pages"]:
            self.meta["date"] = max(p.meta["date"] for p in self.meta["pages"])
        else:
            self.meta["date"] = self.site.generation_time

        self.created_from.add_related("archive", self)


FEATURES = {
    "syndication": SyndicationFeature,
}

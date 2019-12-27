from __future__ import annotations
from typing import Dict, Any, Union, List, Optional
import os
import logging
from staticsite.feature import Feature
from staticsite.theme import PageFilter
from staticsite.page import Page, PageNotFoundError
from staticsite.metadata import Metadata
from staticsite.utils import arrange
import jinja2

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

    # TODO: arrange by syndication_date instead of date
    return arrange(pages, "-date", limit=limit)


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
        self.site.tracked_metadata.add("syndication")
        self.site.features["rst"].yaml_tags.add("syndication")
        self.site.register_metadata(Metadata("syndication", inherited=False, structure=True, doc="""
Defines syndication for the contents of this page.

It is a structure which can contain various fields:

* `add_to`: chooses which pages will include a link to the RSS/Atom feeds
* `pages`: chooses which pages are shown in the RSS/Atom feeds

Any other metadata found in the structure are used when generating pages for
the RSS/Atom feeds, so you can use `title`, `template_title`, `description`,
and so on, to personalize the feeds.

`pages` and `add_to` are dictionaries that select pages in the site, similar
to the `site_pages` function in [templates](templates.md). See
[Selecting pages](page-filter.md) for details.

`pages` is optional, and if missing, `page.meta.pages` is used. Compared to
using the `pages` filter, using `syndication.pages` takes the
[`syndicated` and `syndication_date` page metadata](doc/reference/metadata.md) into account.

For compatibility, `filter` can be used instead of `pages`.

Before rendering, `pages` is replaced with the list of syndicated pages, sorted
with the most recent first.
"""))
        self.site.register_metadata(MetadataSyndicated("syndicated", inherited=False, doc="""
Set to true if the page can be included in a syndication, else to false.

If not set, it defaults to the value of `indexed`.
"""))
        self.site.register_metadata(MetadataSyndicationDate("syndication_date", inherited=False, doc=f"""
Syndication date for this page.

This is the date that will appear in RSS and Atom feeds, and the page will not
be syndicated before this date.

If a page is syndicated and `syndication_date` is missing, it defaults to `date`.
"""))
        self.syndications = []

        self.j2_globals["syndicated_pages"] = self.jinja2_syndicated_pages

    @jinja2.contextfunction
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
                # TODO: arrange by syndication_date
                return arrange(what, "-date", limit=limit)
        except SyndicatedPageError as e:
            log.warn("%s: %s", context.name, e)
            return []

    def prepare_syndication_list(self, pages):
        """
        Given a list of pages to potentially syndicate, filter them by their
        syndicated header, and sort by syndication date.
        """
        res = []
        for page in pages:
            if not page.meta["syndicated"]:
                continue
            if page.meta["syndication_date"] > self.site.generation_time:
                continue
            res.append(page)
        res.sort(key=lambda p: p.meta["syndication_date"], reverse=True)
        return res

    def finalize(self):
        # Build syndications from pages with a 'syndication' metadata
        for page in self.site.pages_by_metadata["syndication"]:
            syndication_meta = page.meta.get("syndication")
            if syndication_meta is None:
                continue

            # Make a shallow copy to prevent undesired side effects if multiple
            # pages share the same syndication dict, as may be the case with
            # taxonomies
            syndication_meta = dict(syndication_meta)
            syndication_meta["site_path"] = page.meta["site_path"]
            page.meta["syndication"] = syndication_meta

            # Index page for the syndication
            syndication_meta["index"] = page

            # Pages in the syndication
            select = syndication_meta.get("pages")
            if select is None:
                # TODO: raise DeprecationWarning suggesting pages?
                select = syndication_meta.get("filter")
            if select:
                f = PageFilter(self.site, **select)
                pages = f.filter(self.site.pages.values())
            else:
                pages = page.meta.get("pages", [])

            syndication_meta["pages"] = self.prepare_syndication_list(pages)

            # Set page.meta.pages if not present
            if "pages" not in page.meta:
                page.meta["pages"] = syndication_meta["pages"]

            self.site.theme.precompile_metadata_templates(syndication_meta)

            # RSS feed
            rss_page = RSSPage(page.parent, syndication_meta)
            if rss_page.is_valid():
                syndication_meta["rss_page"] = rss_page
                self.site.add_page(rss_page)
                log.debug("%s: adding syndication page for %s", rss_page, page)

            # Atom feed
            atom_page = AtomPage(page.parent, syndication_meta)
            if atom_page.is_valid():
                syndication_meta["atom_page"] = atom_page
                self.site.add_page(atom_page)
                log.debug("%s: adding syndication page for %s", rss_page, page)

            # Add a link to the syndication to the pages listed in add_to
            add_to = syndication_meta.get("add_to")
            if add_to:
                f = PageFilter(self.site, **add_to)
                for dest in f.filter(self.site.pages.values()):
                    if dest == page:
                        continue
                    old = dest.meta.get("syndication")
                    if old is not None:
                        log.warn("%s: attempted to add meta.syndication from %r, but it already has it from %r",
                                 dest, page, old["index"])
                    dest.meta["syndication"] = syndication_meta


class SyndicationPage(Page):
    """
    Base class for syndication pages
    """
    # Default template to use for this type of page
    TEMPLATE: str

    def __init__(self, parent: Page, meta: Dict[str, Any]):
        index = meta["index"]
        meta = dict(meta)
        meta["site_path"] = os.path.join(meta["site_path"], f"index.{self.TYPE}")

        super().__init__(
            parent=parent,
            src=None,
            meta=meta)
        self.meta["build_path"] = meta["site_path"]
        self.meta.setdefault("template", self.TEMPLATE)
        if self.meta["pages"]:
            self.meta["date"] = max(p.meta["date"] for p in self.meta["pages"])
        else:
            self.meta["date"] = self.site.generation_time

        # Copy well known keys from index page
        for key in "site_root", "site_url", "author", "site_name":
            self.meta.setdefault(key, index.meta.get(key))


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


FEATURES = {
    "syndication": SyndicationFeature,
}

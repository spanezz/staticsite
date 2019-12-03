from __future__ import annotations
from typing import Dict, Any, Optional, Union
from staticsite.feature import Feature
from staticsite.theme import PageFilter
from staticsite.render import RenderedString
from staticsite import Page, Site, File
import os
import logging

log = logging.getLogger()


class SyndicationInfo:
    def __init__(self, index_page: Page, syndication: Dict[str, Any] = None):
        if syndication is None:
            syndication = {}
        self.index_page = index_page
        self.meta = syndication

        # Dict with PageFilter arguments to select the pages to show in this
        # syndication
        select = syndication.get("filter")
        self.select: Optional[Dict[str, Any]] = dict(select) if select is not None else None

        # Dict with PageFilter arguments to select the pages that should link
        # to this syndication
        add_to = syndication.get("add_to")
        self.add_to: Optional[Dict[str, Any]] = dict(add_to) if add_to is not None else None

        # link: defaults to same page: link shown as feed link
        link = syndication.get("link")
        self.link: Union[Page, str] = index_page if link is None else str(link)

        # Pages included in this syndication
        self.pages = []

        # RSS page for this syndication
        self.rss_page: Optional[Page] = None

        # Atom page for this syndication
        self.atom_page: Optional[Page] = None


class SyndicationFeature(Feature):
    """
    Build syndication feeds for groups of pages.

    One page is used to define the syndication, using "syndication_*" tags.

    Use a data page without type to define a contentless syndication page
    """
    RUN_AFTER = ["rst", "tags", "dirs"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.for_metadata.append("syndication")
        self.site.features["rst"].yaml_tags.add("syndication")
        self.syndications = []

    def add_page(self, page):
        syndication = page.meta.get("syndication", None)
        if syndication is None:
            return

        syndication_info = SyndicationInfo(page, syndication)
        self.syndications.append(syndication_info)
        page.meta["syndication_info"] = syndication_info

    def finalize(self):
        # Add syndication info for all taxonomies
        for taxonomy in self.site.features["tags"].taxonomies.values():
            # For each item in the taxonomy, create a syndication
            for category_page in taxonomy.categories.values():
                info = SyndicationInfo(category_page, category_page.meta.get("syndication"))
                info.pages = category_page.pages
                self.syndications.append(info)
                category_page.meta["syndication_info"] = info
                category_page.archive.meta["syndication_info"] = info

        for syndication_info in self.syndications:
            # Compute the pages to show
            if syndication_info.select:
                f = PageFilter(self.site, **syndication_info.select)
                syndication_info.pages.extend(f.filter(self.site.pages.values()))

            # Add a link to the syndication to the affected pages
            if syndication_info.add_to:
                f = PageFilter(self.site, **syndication_info.add_to)
                for page in f.filter(self.site.pages.values()):
                    page.meta["syndication_info"] = syndication_info

            # Expand the link
            if isinstance(syndication_info.link, str):
                syndication_info.link = syndication_info.index_page.resolve_uri(syndication_info.link)

            # Generate the syndication pages in the site
            rss_page = RSSPage(self.site, syndication_info)
            syndication_info.rss_page = rss_page
            self.site.pages[rss_page.src_linkpath] = rss_page
            log.debug("%s: adding syndication page for %s", rss_page, syndication_info.index_page)

            atom_page = AtomPage(self.site, syndication_info)
            syndication_info.atom_page = atom_page
            self.site.pages[atom_page.src_linkpath] = atom_page
            log.debug("%s: adding syndication page for %s", rss_page, syndication_info.index_page)

        # filter: args to page filters
        # link: defaults to same page: link shown as feed link
        # add_to: args to page filters
        #  - shortcut to define 'filters' but without limit?
        # title
        # date: autocomputed


class SyndicationPage(Page):
    """
    Base class for syndication pages
    """
    RENDER_PREFERRED_ORDER = 2

    def __init__(self, site: Site, info: SyndicationInfo):
        relpath = f"{info.index_page.src_linkpath}.{self.TYPE}"

        super().__init__(
            site=site,
            src=File(relpath=relpath),
            src_linkpath=relpath,
            dst_relpath=relpath,
            dst_link=os.path.join(site.settings.SITE_ROOT, relpath),
            meta=info.meta)

        if self.meta.get("title") is None:
            self.meta["title"] = info.index_page.meta.get("title")

        if self.meta.get("title") is None:
            log.warn("%s: syndication index page %s has no title", self, info.index_page)
            self.meta["title"] = self.site.site_name

        if self.meta.get("date") is None:
            if info.pages:
                self.meta["date"] = max(p.meta["date"] for p in info.pages)
            else:
                self.meta["date"] = self.site.generation_time

        self.meta["index"] = info.index_page
        self.info = info

        self.template = self.site.theme.jinja2.get_template(self.TEMPLATE)

        self.validate_meta()

    def render(self):
        body = self.render_template(self.template, {
            "title_page": self.info.link,
            "pages": self.info.pages,
        })
        return {
            self.dst_relpath: RenderedString(body)
        }


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

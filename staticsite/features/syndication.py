from __future__ import annotations
from typing import Dict, Any, Optional
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

            # Generate the syndication pages in the site
            rss_page = RSSPage(self.site, syndication_info)
            if rss_page.is_valid():
                syndication_info.rss_page = rss_page
                self.site.pages[rss_page.src_linkpath] = rss_page
                log.debug("%s: adding syndication page for %s", rss_page, syndication_info.index_page)

            atom_page = AtomPage(self.site, syndication_info)
            if atom_page.is_valid():
                syndication_info.atom_page = atom_page
                self.site.pages[atom_page.src_linkpath] = atom_page
                log.debug("%s: adding syndication page for %s", rss_page, syndication_info.index_page)


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

        # Hardcode the template
        # FIXME: allow to customize it in syndication metadata?
        self.meta["template"] = self.TEMPLATE

        self.meta["index"] = info.index_page
        self.info = info

    def is_valid(self):
        if not self.meta.get("title") and not self.meta.get("template_title"):
            if self.info.index_page.meta.get("title"):
                self.meta["title"] = self.info.index_page.meta.get("title")
            elif self.info.index_page.meta.get("template_title"):
                self.meta["template_title"] = self.info.index_page.meta.get("template_title")
            else:
                log.warn("%s: syndication index page %s has no title", self, self.info.index_page)
                self.meta["title"] = self.site.site_name

        if not self.meta.get("description") and not self.meta.get("template_description"):
            if self.info.index_page.meta.get("description"):
                self.meta["description"] = self.info.index_page.meta.get("description")
            elif self.info.index_page.meta.get("template_description"):
                self.meta["template_description"] = self.info.index_page.meta.get("template_description")

        if self.meta.get("date") is None:
            if self.info.pages:
                self.meta["date"] = max(p.meta["date"] for p in self.info.pages)
            else:
                self.meta["date"] = self.site.generation_time

        if not super().is_valid():
            return False

        return True

    def render(self):
        body = self.render_template(self.page_template, {
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
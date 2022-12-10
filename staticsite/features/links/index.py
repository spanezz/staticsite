from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from staticsite.page import Page

from .data import Link, LinkCollection

if TYPE_CHECKING:
    from . import Links

log = logging.getLogger("links")


class LinkIndexPage(Page):
    """
    Root page for the browseable archive of annotated external links in the
    site
    """
    TYPE = "links_index"
    TEMPLATE = "data-links.html"

    def __init__(self, *args, name: str, links: Links, **kw):
        kw.setdefault("nav_title", name.capitalize())
        kw.setdefault("title", "All links shared in the site")
        super().__init__(*args, **kw)
        # Reference to the Feature with the aggregated link collection
        self.feature_links = links

        self.by_tag: dict[str, "LinksTagPage"] = {}

#    def to_dict(self):
#        from staticsite.utils import dump_meta
#        res = super().to_dict()
#        res["name"] = self.name
#        res["categories"] = dump_meta(self.categories)
#        res["category_meta"] = dump_meta(self.category_meta)
#        return res

    def analyze(self):
        pages = []
        for tag, links in self.feature_links.by_tag.items():
            name = tag + "-links"
            sub = self.node.child(name)

            if sub.page is not None:
                # A page already exists
                continue

            page = sub.create_page(
                    created_from=self,
                    page_cls=LinksTagPage,
                    data_type="links",
                    title=f"{tag} links",
                    links=links,
                    directory_index=True)
            self.by_tag[tag] = page
            pages.append(page)

        # Set self.meta.pages to the sorted list of categories
        pages.sort(key=lambda x: x.title)
        self.pages = pages
        self.link_collection = self.feature_links.links


class LinksTagPage(Page):
    """
    Page with an autogenerated link collection from a link tag.
    """
    TYPE = "links_tag"
    TEMPLATE = "data-links.html"

    def __init__(self, *args, **kw):
        links = kw.pop("links", None)
        super().__init__(*args, **kw)
        self.syndicated = False
        if links is None:
            self.link_collection = LinkCollection([Link(link) for link in self.links])
        else:
            self.link_collection = links

    @property
    def src_abspath(self):
        return None

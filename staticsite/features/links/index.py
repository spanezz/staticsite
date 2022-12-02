from __future__ import annotations
from typing import TYPE_CHECKING
import logging
from staticsite import Page
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

    def __init__(self, *args, name: str, links: Links, **kw):
        super().__init__(*args, **kw)
        # Reference to the Feature with the aggregated link collection
        self.feature_links = links

        self.meta.setdefault("template", "data-links.html")
        self.meta.setdefault("nav_title", name.capitalize())
        self.meta.setdefault("title", "All links shared in the site")

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
                    meta_values={
                        "data_type": "links",
                        "title": f"{tag} links",
                        "links": links,
                    },
                    links=links,
                    directory_index=True)
            self.by_tag[tag] = page
            pages.append(page)

        # Set self.meta.pages to the sorted list of categories
        pages.sort(key=lambda x: x.meta["title"])
        self.meta["pages"] = pages
        self.links = self.feature_links.links


class LinksTagPage(Page):
    """
    Page with an autogenerated link collection from a link tag.
    """
    TYPE = "links_tag"

    def __init__(self, *args, **kw):
        links = kw.pop("links", None)
        super().__init__(*args, **kw)
        self.meta["syndicated"] = False
        self.meta.setdefault("template", "data-links.html")
        if links is None:
            self.links = LinkCollection([Link(link) for link in self.meta["links"]])
        else:
            self.links = links

    @property
    def src_abspath(self):
        return None

from __future__ import annotations
import jinja2
import os
import logging
from collections import Counter, defaultdict
from staticsite.feature import Feature
from staticsite.features.data import DataPage
from staticsite.page_filter import PageFilter

log = logging.getLogger("links")


class Link:
    """
    All known information about one external link
    """
    def __init__(self, info, page=None):
        self.page = page
        self.url = info.get("url")
        self.title = info.get("title")
        self.tags = set(info.get("tags", ()))
        self.archive = info.get("archive")
        self.related = info.get("related", ())
        self.abstract = info.get("abstract")


class LinkCollection:
    """
    Collection of links
    """
    def __init__(self, links=None):
        self.links = links if links is not None else []

        # Compute count of link and tag cardinalities
        self.card = Counter()
        for link in self.links:
            for tag in link.tags:
                self.card[tag] += 1

    def __iter__(self):
        return iter(self.links)

    def __len__(self):
        return len(self.links)

    def __bool__(self):
        return bool(self.links)

    def tags_and_cards(self):
        """
        Return a list of (tag, card) for all tags in the collection
        """
        res = list((tag, card) for tag, card in self.card.most_common() if card < len(self.links))
        res.sort(key=lambda x: (-x[1], x[0]))
        return res

    def append(self, link):
        self.links.append(link)
        for tag in link.tags:
            self.card[tag] += 1

    def merge(self, coll):
        self.links.extend(coll.links)
        self.card += coll.card

#    def most_selective_tag(self):
#        """
#        Return tag in a collection of links that best partitions the collection
#        into two groups of a similar size
#        """
#        count = len(self.links)
#
#        def score(tag):
#            card = self.card[tag]
#            return (count - card) / count
#
#        tag = min(self.card.keys(), key=score)
#        if self.card[tag] < 4:
#            return None
#        return tag
#
#    def partition(self, tag):
#        """
#        Return two LinkCollection objects, one for links with tag, one for
#        links without
#        """
#        selected = []
#        not_selected = []
#        for link in self.links:
#            if tag in link.tags:
#                selected.append(link)
#            else:
#                not_selected.append(link)
#
#        return LinkCollection(selected), LinkCollection(not_selected)

    def make_groups(self):
        """
        Compute groups from links.

        Return a dict with the grouper tag mapped to the grouped links
        """
        seen = set()
        groups = []
        for tag, card in self.card.most_common():
            if card < 4:
                break
            selected = [l for l in self.links if tag in l.tags]
            if len(selected) == len(self.links):
                continue
            seen.update(l.url for l in selected)
            groups.append((tag, LinkCollection(selected)))

        groups.sort()

        others = [l for l in self.links if l.url not in seen]
        if others:
            # If all elements in other share a tag, use that instead of None
            other_tag = None
            common_tags = set.intersection(*(l.tags for l in others))
            if common_tags:
                other_tag = sorted(common_tags)[0]
            groups.append((other_tag, LinkCollection(others)))

#        remainder = self
#
#        groups = {}
#        while remainder:
#            tag = remainder.most_selective_tag()
#            if tag is None:
#                groups[None] = remainder
#                break
#            groups[tag], remainder = remainder.partition(tag)
#
        return groups


class LinksPage(DataPage):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.links = LinkCollection([Link(link, page=self) for link in self.meta["links"]])


class LinksTagPage(DataPage):
    def __init__(self, *args, **kw):
        links = kw.pop("links", None)
        super().__init__(*args, **kw)
        self.meta["syndicated"] = False
        if links is None:
            self.links = LinkCollection([Link(link) for link in self.meta["links"]])
        else:
            self.links = links

    @property
    def src_abspath(self):
        return None


class Links(Feature):
    RUN_AFTER = ["data"]
    RUN_BEFORE = ["dirs"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.j2_globals["links_merged"] = self.links_merged
        self.j2_globals["links_tag_index_url"] = self.links_tag_index_url
        self.data = self.site.features["data"]
        self.data.register_page_class("links", LinksPage)

    @jinja2.contextfunction
    def links_merged(self, context, path=None, limit=None, sort=None, link_tags=None, **kw):
        page_filter = PageFilter(self.site, path=path, limit=limit, sort=sort, **kw)

        # Build link tag filter
        if link_tags is not None:
            if isinstance(link_tags, str):
                link_tags = {link_tags}
            else:
                link_tags = set(link_tags)

        links = LinkCollection()
        if link_tags is None:
            for page in page_filter.filter(self.data.by_type.get("links", ())):
                links.merge(page.links)
        else:
            for page in page_filter.filter(self.data.by_type.get("links", ())):
                for link in page.links:
                    if link_tags is not None and not link_tags.issubset(link.tags):
                        continue
                    links.append(link)

        return links

    @jinja2.contextfunction
    def links_tag_index_url(self, context, tag):
        return os.path.join(self.site.settings.SITE_ROOT, "links", tag + "-links")

    def finalize(self):
        # Index links by tag
        by_tag = defaultdict(LinkCollection)
        for page in self.data.by_type.get("links", ()):
            for link in page.links:
                for tag in link.tags:
                    by_tag[tag].append(link)

        # TODO: since we hardcode link pages on /links/*, we hardcode taking
        # default page metadata from the root. We can do better if we place a
        # .links page, similar to .taxonomy, where we want them mounted
        dir_meta = self.site.content_roots[0].meta
        for tag, links in by_tag.items():
            # FIXME: this hardcodes the path to the root
            meta = dict(dir_meta)
            meta["site_path"] = os.path.join(meta["site_path"], "links", tag + "-links")
            if meta["site_path"] in self.site.pages:
                continue
            meta["data_type"] = "links"
            meta["title"] = f"{tag} links"
            meta["links"] = links
            page = LinksTagPage.create_from(self.site.content_roots[0], meta, links=links)
            self.site.add_page(page)

    def add_site_commands(self, subparsers):
        super().add_site_commands(subparsers)
        from .links import LinkLint
        LinkLint.make_subparser(subparsers)


FEATURES = {
    "links": Links,
}

from __future__ import annotations
from collections import Counter
import logging

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

        return groups

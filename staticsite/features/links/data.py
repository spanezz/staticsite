from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING, Any, Iterable, Optional, Sequence

if TYPE_CHECKING:
    from staticsite.page import Page

log = logging.getLogger("links")


class Link:
    """
    All known information about one external link
    """
    def __init__(self, info: dict[str, Any], page: Optional[Page] = None):
        self.page = page
        self.url: str = info["url"]
        self.title: str = info["title"]
        self.tags: set[str] = set(info.get("tags", ()))
        self.archive: Optional[str] = info.get("archive")
        self.related: Sequence[str] = info.get("related", ())
        self.abstract: Optional[str] = info.get("abstract")

    def as_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {"url": self.url}
        if self.title:
            res["title"] = self.title
        if self.tags:
            res["tags"] = list(self.tags)
        if self.archive:
            res["archive"] = self.archive
        if self.related:
            res["related"] = self.related
        if self.abstract:
            res["abstract"] = self.abstract
        return res


class LinkCollection:
    """
    Collection of links
    """
    def __init__(self, links: Optional[dict[str, Link]] = None):
        self.links: dict[str, Link] = links if links is not None else {}

        # Compute count of link and tag cardinalities
        self.card: Counter[str] = Counter()
        for link in self.links.values():
            for tag in link.tags:
                self.card[tag] += 1

    def __iter__(self) -> Iterable[Link]:
        return self.links.values().__iter__()

    def __len__(self) -> int:
        return len(self.links)

    def __bool__(self) -> bool:
        return bool(self.links)

    def get(self, url: str) -> Optional[Link]:
        return self.links.get(url)

    def tags_and_cards(self) -> list[tuple[str, int]]:
        """
        Return a list of (tag, card) for all tags in the collection
        """
        res = list((tag, card) for tag, card in self.card.most_common() if card < len(self.links))
        res.sort(key=lambda x: (-x[1], x[0]))
        return res

    def append(self, link: Link) -> None:
        self.links[link.url] = link
        for tag in link.tags:
            self.card[tag] += 1

    def merge(self, coll: LinkCollection) -> None:
        self.links.update(coll.links)
        self.card += coll.card

    def make_groups(self) -> list[tuple[Optional[str], LinkCollection]]:
        """
        Compute groups from links.

        Return a dict with the grouper tag mapped to the grouped links
        """
        seen: set[str] = set()
        groups: list[tuple[Optional[str], LinkCollection]] = []
        for tag, card in self.card.most_common():
            if card < 4:
                break
            selected = {link.url: link for link in self.links.values() if tag in link.tags}
            if len(selected) == len(self.links):
                continue
            seen.update(link.url for link in selected.values())
            groups.append((tag, LinkCollection(selected)))

        groups.sort()

        others = {link.url: link for link in self.links.values() if link.url not in seen}
        if others:
            # If all elements in other share a tag, use that instead of None
            other_tag: Optional[str] = None
            common_tags: set[str] = set.intersection(*(link.tags for link in others.values()))
            if common_tags:
                other_tag = sorted(common_tags)[0]
            groups.append((other_tag, LinkCollection(others)))

        return groups

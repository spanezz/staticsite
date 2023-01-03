from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, cast

from staticsite.cmd.site import FeatureCommand

if TYPE_CHECKING:
    from staticsite.features.data import DataPages
    from staticsite.features.links import LinksPage

log = logging.getLogger("links")


class LinkLint(FeatureCommand):
    "run consistency checks on links data"

    NAME = "link_lint"

    def run(self) -> None:
        # links = self.site.features["links"]
        seen = defaultdict(list)
        data = cast(DataPages, self.site.features["data"])
        for lpage in data.by_type.get("links", ()):
            page = cast(LinksPage, lpage)
            if not page.links:
                continue
            for link in page.links:
                seen[link.url].append(page)

        for url, pages in seen.items():
            if len(pages) == 1:
                continue
            print(f"{url}: link appears in multiple pages:")
            for page in pages:
                print(f" - {page.src.relpath}")

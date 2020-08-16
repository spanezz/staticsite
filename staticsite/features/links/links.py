from __future__ import annotations
import logging
from collections import defaultdict
from staticsite.cmd.site import FeatureCommand

log = logging.getLogger("links")


class LinkLint(FeatureCommand):
    "run consistency checks on links data"

    NAME = "link_lint"

    def run(self):
        # links = self.site.features["links"]
        seen = defaultdict(list)
        data = self.site.features["data"]
        for page in data.by_type.get("links", ()):
            for link in page.links:
                seen[link.url].append(page)

        for url, pages in seen.items():
            if len(pages) == 1:
                continue
            print(f"{url}: link appears in multiple pages:")
            for page in pages:
                print(f" - {page.src.relpath}")

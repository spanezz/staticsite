from __future__ import annotations

import datetime
import logging
from collections import Counter
from typing import TYPE_CHECKING

from staticsite.utils import timings

from .command import SiteCommand, register

if TYPE_CHECKING:
    from ..site import Site

log = logging.getLogger("check")


@register
class Check(SiteCommand):
    "check the site, going through all the motions of rendering it without writing anything"

    def run(self) -> None:
        site = self.load_site()
        with timings("Checked site in %fs"):
            self.check(site)

    def check(self, site: Site) -> None:
        counts: dict[str, int] = Counter()
        for page in site.iter_pages():
            counts[page.TYPE] += 1
            page.check()

            date = page.meta.get("date", None)
            if date is not None:
                if not isinstance(date, datetime.datetime):
                    log.info(
                        "%r: meta date %r is not an instance of datetime", page, date
                    )

        for type, count in sorted(counts.items()):
            print(f"{count} {type} pages")

import datetime
from staticsite.utils import timings
from collections import Counter
from .command import SiteCommand
import logging

log = logging.getLogger()


class Check(SiteCommand):
    "check the site, going through all the motions of rendering it without writing anything"

    def run(self):
        site = self.load_site()
        with timings("Checked site in %fs"):
            self.check(site)

    def check(self, site):
        counts = Counter()
        for page in site.pages.values():
            counts[page.TYPE] += 1
            page.check(self)

            date = page.meta.get("date", None)
            if date is not None:
                if not isinstance(date, datetime.datetime):
                    log.info("%s: meta date %r is not an instance of datetime", page.src.relpath, date)

        for type, count in sorted(counts.items()):
            print("{} {} pages".format(count, type))

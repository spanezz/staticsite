# coding: utf-8

#from .core import BodyWriter, MarkdownPage
import os
import shutil
import json
import datetime
from collections import Counter
import logging

log = logging.getLogger()

#class BodyChecker(BodyWriter):
#    pass


class Checker:
    def check(self, site):
        counts = Counter()
        for page in site.pages.values():
            counts[page.TYPE] += 1
            page.check(self)

            date = page.meta.get("date", None)
            if date is not None:
                if not isinstance(date, datetime.datetime):
                    log.info("%s: meta date %r is not an instance of datetime", page.src_relpath, date)

        for type, count in sorted(counts.items()):
            print("{} {} pages".format(count, type))

# coding: utf-8

#from .core import BodyWriter, MarkdownPage
import os
import shutil
import json
from collections import Counter
import logging

log = logging.getLogger()

#class BodyChecker(BodyWriter):
#    pass


class Checker:
    def write(self, site):
        counts = Counter()
        for page in site.pages.values():
            counts[page.TYPE] += 1
            page.check(self)

        for type, count in sorted(counts.items()):
            print("{} {} pages".format(count, type))

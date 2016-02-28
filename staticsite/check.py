# coding: utf-8

from .core import BodyWriter, MarkdownPage
import os
import shutil
import json
from collections import Counter
import logging

log = logging.getLogger()

class BodyChecker(BodyWriter):
    pass


class Checker:
    def write(self, site):
        counts = Counter()
        for page in site.pages.values():
            # TODO: run a checker on the parsed body
            counts[page.TYPE] += 1
            getattr(self, "check_" + page.TYPE)(page)

        for type, count in sorted(counts.items()):
            print("{} {} pages".format(count, type))


    def check_static(self, page):
        pass

    def check_markdown(self, page):
        checker = BodyChecker()
        checker.read(page)

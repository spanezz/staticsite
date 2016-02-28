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
    def __init__(self):
        # Markdown compiler
        from . import markdown as ssite_markdown
        self.markdown = ssite_markdown.Renderer()

    def write(self, site):
        counts = Counter()
        for page in site.pages.values():
            counts[page.TYPE] += 1
            getattr(self, "check_" + page.TYPE)(page)

        for type, count in sorted(counts.items()):
            print("{} {} pages".format(count, type))


    def check_asset(self, page):
        pass

    def check_markdown(self, page):
        self.markdown.render(page)

    def check_jinja2(self, page):
        pass

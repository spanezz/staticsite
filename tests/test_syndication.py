from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils
import re


class TestSyndication(TestCase):
    def test_simple(self):
        site = test_utils.Site(
            THEME="example/theme",
        )
        site.load_without_content()

        blog = site.add_test_page(
            "md",
            relpath="blog.md",
            content="""---
date: 2016-04-16 10:23:00+02:00
syndication:
  filter:
    path: blog/*
    limit: 5
    sort: "-date"
  add_to:
    path: blog/*
---

# Title

text
""")

        post = site.add_test_page(
            "rst",
            relpath="blog/post.rst",
            content="""
:date: 2016-04-16 10:23:00+02:00

Example blog post in reStructuredText
=====================================
""")

        site.analyze()

        self.assertIn("syndication_info", blog.meta)
        self.assertIn("syndication_info", post.meta)

        # See what the site would generate
        rendered_pages = {}
        for page in site.pages.values():
            contents = page.render()
            for relpath, rendered in contents.items():
                # Ignore static assets
                if re.match(r"^(fork-awesome|popper\.js|bootstrap4|jquery|css|images)/", relpath):
                    continue
                rendered_pages[relpath] = [page, rendered]

        self.maxDiff = None
        self.assertCountEqual(rendered_pages.keys(), [
            "index.html",
            "blog/index.html",
            "blog.rss",
            "blog.atom",
            "blog/post/index.html",
        ])

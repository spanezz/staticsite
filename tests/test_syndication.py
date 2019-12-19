from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils


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

        self.assertIn("syndication", blog.meta)
        self.assertIn("syndication", post.meta)

        # See what the site would generate
        rendered_pages = {}
        for page in site.pages.values():
            contents = page.render()
            for relpath, rendered in contents.items():
                # Ignore static assets
                if relpath.startswith("static/"):
                    continue
                rendered_pages[relpath] = [page, rendered]

        self.maxDiff = None
        self.assertCountEqual(rendered_pages.keys(), [
            "index.html",
            "blog/index.html",
            "blog/index.rss",
            "blog/index.atom",
            "blog/post/index.html",
        ])

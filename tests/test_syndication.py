from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils


class TestSyndication(TestCase):
    def test_simple(self):
        files = {
            "blog.md": """---
date: 2016-04-16 10:23:00+02:00
syndication:
  filter:
    path: blog/*
  add_to:
    path: blog/*
---

# Title

text
""",
            "blog/post.rst": """
:date: 2016-04-16 10:23:00+02:00

Example blog post in reStructuredText
=====================================
""",
        }

        with test_utils.workdir(files) as root:
            site = test_utils.Site(CONTENT=root)
            site.load()
            site.analyze()

            blog = site.pages["blog"]
            self.assertIn("syndication", blog.meta)
            post = site.pages["blog/post"]
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

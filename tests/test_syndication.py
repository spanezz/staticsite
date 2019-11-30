from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils
import datetime


class TestSyndication(TestCase):
    def test_simple(self):
        site = test_utils.Site()
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

#        # We have a root dir index and dir indices for all subdirs
#        page = site.pages[""]
#        self.assertEqual(page.TYPE, "rst")
#        self.assertEqual(page.meta, {
#            "date": datetime.datetime(2016, 4, 16, 10, 23, tzinfo=site.timezone),
#            "tags": ["example", "another tag"],
#            "foo": "line1\nline2\nline3\n",
#        })

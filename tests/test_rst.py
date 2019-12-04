from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils
from dateutil import tz
import datetime


class TestRst(TestCase):
    def test_simple(self):
        site = test_utils.Site(TAXONOMIES=["tags"])
        site.load_without_content()

        site.add_test_page(
            "rst",
            relpath="index.rst",
            content="""
:date: 2016-04-16 10:23:00+02:00
:tags: [example, "another tag"]
:foo:
  line1
  line2
  line3

Example blog post in reStructuredText
=====================================
""")
        tags = site.add_test_page("tags", name="tags")

        site.analyze()

        tag_example = tags.categories["example"]
        tag_another = tags.categories["another tag"]

        # We have a root dir index and dir indices for all subdirs
        page = site.pages[""]
        self.assertEqual(page.TYPE, "rst")
        self.assertCountEqual(page.meta.pop("tags"), [tag_example, tag_another])
        self.assertEqual(page.meta, {
            "date": datetime.datetime(2016, 4, 16, 10, 23, tzinfo=tz.tzoffset(None, 7200)),
            "foo": "line1\nline2\nline3",
            "template": "page.html",
            "title": "Example blog post in reStructuredText",
        })
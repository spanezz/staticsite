from unittest import TestCase
from staticsite.cmd.build import Build
from . import utils as test_utils
import datetime


class TestRst(TestCase):
    def test_simple(self):
        site = test_utils.Site()
        site.load_without_content()

        site.add_test_page(
            "rst",
            relpath="index.rst",
            content="""
:date: 2016-04-16 10:23:00+02:00
:tags: example, "another tag"
:foo:
  line1
  line2
  line3

Example blog post in reStructuredText
=====================================
""")

        site.analyze()

        # We have a root dir index and dir indices for all subdirs
        page = site.pages[""]
        self.assertEqual(page.TYPE, "rst")
        self.assertEqual(page.meta, {
            "date": datetime.datetime(2016, 4, 16, 10, 23, tzinfo=site.timezone),
            "tags": ["example", "another tag"],
            "foo": "line1\nline2\nline3\n",
        })

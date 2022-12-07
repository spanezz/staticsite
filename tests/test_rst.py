from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils
import os


class TestRst(test_utils.MockSiteTestMixin, TestCase):
    def test_simple(self):
        self.maxDiff = None

        files = {
            "taxonomies/tags.taxonomy": {},
            "index.rst": """
:date: 2016-04-16 10:23:00+02:00
:tags: [example, "another tag"]
:foo:
  line1
  line2
  line3

Example blog post in reStructuredText
=====================================
""",
        }

        with self.site(files) as mocksite:
            page, tags, tag_example, tag_another = mocksite.page("", "taxonomies/tags", "example", "another tag")

            # We have a root dir index and dir indices for all subdirs
            self.assertEqual(page.TYPE, "rst")
            self.assertCountEqual(page.meta.pop("tags"), [tag_example, tag_another])
            self.assertEqual(page.to_dict(), {
                "src": {
                    "abspath": os.path.join(mocksite.site.content_root, "index.rst"),
                    "relpath": "index.rst",
                },
                "site_path": "",
                "build_path": "index.html",
                "meta": {
                    "author": "Test User",
                    "copyright": '© 2016 Test User',
                    "date": "2016-04-16 10:23:00+02:00",
                    "draft": False,
                    "syndicated": True,
                    "syndication_date": "2016-04-16 10:23:00+02:00",
                    "foo": "line1\nline2\nline3",
                    "template": "page.html",
                    "title": "Example blog post in reStructuredText",
                    "indexed": True,
                    "site_name": "Test site",
                    "site_url": "https://www.example.org",
                    'related': {},
                },
                "type": "rst",
            })

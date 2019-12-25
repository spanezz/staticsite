from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils
import os


class TestRst(TestCase):
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

        with test_utils.workdir(files) as root:
            site = test_utils.Site(PROJECT_ROOT=root)
            site.load()
            site.analyze()

            tags = site.pages["taxonomies/tags"]
            tag_example = tags.categories["example"]
            tag_another = tags.categories["another tag"]

            # We have a root dir index and dir indices for all subdirs
            page = site.pages[""]
            self.assertEqual(page.TYPE, "rst")
            self.assertCountEqual(page.meta.pop("tags"), [tag_example, tag_another])
            self.assertEqual(page.to_dict(), {
                "src": {
                    "abspath": os.path.join(root, "index.rst"),
                    "relpath": "index.rst",
                },
                "meta": {
                    "date": "2016-04-16 10:23:00+02:00",
                    "syndicate": True,
                    "foo": "line1\nline2\nline3",
                    "template": "page.html",
                    "title": "Example blog post in reStructuredText",
                    "indexed": True,
                    "site_name": "Test site",
                    "site_path": "",
                    "site_url": "https://www.example.org",
                },
                "dst_relpath": "index.html",
            })

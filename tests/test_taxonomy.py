from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils
import datetime


class TestTags(test_utils.MockSiteTestMixin, TestCase):
    def test_site(self):
        """
        Test simply assigning pages to taxonomies
        """
        files = {
            "taxonomies/tags.taxonomy": "---\n",
            "page1.md": {"date": str(datetime.datetime(2016, 1, 1)), "tags": ["a", "b"]},
        }
        with self.site(files) as mocksite:
            tags, page1 = mocksite.page("taxonomies/tags", "page1")
            self.assertEqual(tags.categories["a"].meta["pages"], [page1])
            self.assertEqual(tags.categories["b"].meta["pages"], [page1])

    def test_load(self):
        """
        Test simply assigning pages to taxonomies
        """
        files = {
            "taxonomies/tags.taxonomy": "---\n",
            "page.md": """---
tags: [cat]
---
# Title
"""
        }
        with self.site(files) as mocksite:
            tags, page = mocksite.page("taxonomies/tags", "page")
            cat = tags.categories["cat"]
            self.assertEqual(cat.meta["pages"], [page])
            self.assertEqual(page.meta["tags"], [cat])

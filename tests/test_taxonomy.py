from unittest import TestCase
from . import utils as test_utils
import datetime


class TestTags(TestCase):
    def test_site(self):
        """
        Test simply assigning pages to taxonomies
        """
        files = {
            "taxonomies/tags.taxonomy": "---\n",
            "page1.md": {"date": str(datetime.datetime(2016, 1, 1)), "tags": ["a", "b"]},
        }
        with test_utils.workdir(files) as root:
            site = test_utils.Site(taxonomies=["tags"])
            site.load(content_root=root)
            site.analyze()

            tags = site.pages["taxonomies/tags"]
            page1 = site.pages["page1"]

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
        with test_utils.workdir(files) as root:
            site = test_utils.Site(taxonomies=["tags"])
            site.load(content_root=root)
            site.analyze()

            tags = site.pages["taxonomies/tags"]
            cat = tags.categories["cat"]
            page = site.pages["page"]

            self.assertEqual(cat.meta["pages"], [page])
            self.assertEqual(page.meta["tags"], [cat])

from unittest import TestCase
from . import utils as test_utils
import datetime


class TestTags(TestCase):
    def test_site(self):
        """
        Test simply assigning pages to taxonomies
        """
        site = test_utils.Site(TAXONOMIES=["tags"])
        site.load_without_content()

        tax1 = site.add_test_page("tags", name="tags")

        page1 = test_utils.Page(site, "page1", date=datetime.datetime(2016, 1, 1), tags=["a", "b"])
        site.add_page(page1)

        site.analyze()

        self.assertEqual(tax1.categories["a"].pages, [page1])
        self.assertEqual(tax1.categories["b"].pages, [page1])

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
            site = test_utils.Site(TAXONOMIES=["tags"])
            site.load(content_root=root)
            site.analyze()

            tags = site.pages["taxonomies/tags"]
            cat = tags.categories["cat"]
            page = site.pages["page"]

            self.assertEqual(cat.pages, [page])
            self.assertEqual(page.meta["tags"], [cat])

        # tax1 = site.add_test_page("tags", name="tags")

        # page1 = test_utils.Page(site, "page1", date=datetime.datetime(2016, 1, 1), tags=["a", "b"])
        # site.add_page(page1)

        # site.analyze()

        # self.assertEqual(tax1.categories["a"].pages, [page1])
        # self.assertEqual(tax1.categories["b"].pages, [page1])

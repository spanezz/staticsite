from unittest import TestCase
from staticsite.site import Site
from . import TestPage, TestTaxonomyPage
import os
import datetime


class TestTaxonomies(TestCase):
    def test_site(self):
        """
        Test simply assigning pages to taxonomies
        """
        site = Site()
        site.load_theme(os.path.join(os.getcwd(), "example", "theme"))

        tax1 = TestTaxonomyPage(site, "tags", meta={})
        site.add_page(tax1)

        page1 = TestPage(site, "page1", date=datetime.datetime(2016, 1, 1), tags=["a", "b"])
        site.add_page(page1)

        site.analyze()

        self.assertEqual(tax1.items["a"].pages, [page1])
        self.assertEqual(tax1.items["b"].pages, [page1])

    def test_autoseries(self):
        """
        Test autogenerating series from taxonomies
        """
        site = Site()
        site.load_theme(os.path.join(os.getcwd(), "example", "theme"))

        tax1 = TestTaxonomyPage(site, "tags", meta={"series": ["a", "b"]})
        site.add_page(tax1)

        page1 = TestPage(site, "page1", date=datetime.datetime(2016, 1, 1), tags=["a", "b"])
        site.add_page(page1)

        page2 = TestPage(site, "page2", date=datetime.datetime(2016, 1, 2), tags=["a"])
        site.add_page(page2)

        page3 = TestPage(site, "page3", date=datetime.datetime(2016, 1, 3), tags=["a", "b"], series="a")
        site.add_page(page3)

        site.analyze()

        self.assertCountEqual(tax1.items["a"].pages, [page1, page2, page3])
        self.assertCountEqual(tax1.items["b"].pages, [page1, page3])
        self.assertEqual(site.series["a"].pages, [page2, page3])
        self.assertNotIn("b", site.series)

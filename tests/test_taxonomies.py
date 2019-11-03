from unittest import TestCase
from staticsite import Site
from . import TestPage
import os
import datetime


class TestTaxonomies(TestCase):
    def test_site(self):
        """
        Test simply assigning pages to taxonomies
        """
        site = Site()
        site.settings.THEME = os.path.join(os.getcwd(), "example", "theme")
        site.load()

        tax1 = site.add_test_page("taxonomies", name="tags")

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
        site.settings.THEME = os.path.join(os.getcwd(), "example", "theme")
        site.load()

        series = site.features["series"].series

        tax1 = site.add_test_page("taxonomies", name="tags", series_tags=["a", "b"])

        page1 = TestPage(site, "page1", date=datetime.datetime(2016, 1, 1), tags=["a", "b"])
        site.add_page(page1)

        page2 = TestPage(site, "page2", date=datetime.datetime(2016, 1, 2), tags=["a"])
        site.add_page(page2)

        page3 = TestPage(site, "page3", date=datetime.datetime(2016, 1, 3), tags=["a", "b"], series="a")
        site.add_page(page3)

        site.analyze()

        self.assertCountEqual(tax1.items["a"].pages, [page1, page2, page3])
        self.assertCountEqual(tax1.items["b"].pages, [page1, page3])
        self.assertEqual(series["a"].pages, [page1, page2, page3])
        self.assertNotIn("b", series)

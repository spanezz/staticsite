from unittest import TestCase
from . import utils as test_utils
import datetime


class TestTaxonomies(TestCase):
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

    def test_autoseries(self):
        """
        Test autogenerating series from taxonomies
        """
        site = test_utils.Site(TAXONOMIES=["tags"])
        site.load_without_content()

        series = site.features["series"].series

        tax1 = site.add_test_page("tags", name="tags", series_tags=["a", "b"])

        page1 = test_utils.Page(site, "page1", date=datetime.datetime(2016, 1, 1), tags=["a", "b"])
        site.add_page(page1)

        page2 = test_utils.Page(site, "page2", date=datetime.datetime(2016, 1, 2), tags=["a"])
        site.add_page(page2)

        page3 = test_utils.Page(site, "page3", date=datetime.datetime(2016, 1, 3), tags=["a", "b"], series="a")
        site.add_page(page3)

        site.analyze()

        self.assertCountEqual(tax1.categories["a"].pages, [page1, page2, page3])
        self.assertCountEqual(tax1.categories["b"].pages, [page1, page3])
        self.assertEqual(series["a"].pages, [page1, page2, page3])
        self.assertNotIn("b", series)

from unittest import TestCase
from . import utils as test_utils


class TestSite(TestCase):
    def test_titles(self):
        with test_utils.example_site("blog") as site:
            page = site.pages["/about"]
            self.assertEqual(page.meta["title"], "About")

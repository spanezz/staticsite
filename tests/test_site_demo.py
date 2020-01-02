from unittest import TestCase
from . import utils as test_utils


class TestSite(TestCase):
    def test_titles(self):
        with test_utils.example_site("demo") as site:
            page = site.pages["/tags/example"]
            self.assertIsNotNone(page.meta["template_title"])
            self.assertEqual(page.meta["title"], "Latest posts for tag <strong>example</strong>")

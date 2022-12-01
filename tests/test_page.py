from __future__ import annotations

from unittest import TestCase

from . import utils as test_utils


class TestPage(TestCase):
    def test_resolve_path(self):
        files = {
            "toplevel.md": {},
            "lev1/page1.md": {},
            "lev1/page2.md": {},
            "lev1/lev2/page1.md": {},
        }
        with test_utils.testsite(files) as site:
            toplevel = site.pages["toplevel"]
            lev1page1 = site.pages["lev1/page1"]
            lev1page2 = site.pages["lev1/page2"]
            lev2page1 = site.pages["lev1/lev2/page1"]

            self.assertEqual(lev1page1.resolve_path("/lev1/page2.md"), lev1page2)
            self.assertEqual(lev1page1.resolve_path("/lev1/page2"), lev1page2)
            self.assertEqual(lev1page1.resolve_path("page2.md"), lev1page2)
            self.assertEqual(lev1page1.resolve_path("page2"), lev1page2)

            self.assertEqual(lev1page1.resolve_path("../toplevel.md"), toplevel)
            self.assertEqual(lev1page1.resolve_path("../toplevel"), toplevel)
            self.assertEqual(lev1page1.resolve_path("/toplevel.md"), toplevel)
            self.assertEqual(lev1page1.resolve_path("/toplevel"), toplevel)

            self.assertEqual(lev1page1.resolve_path("/lev1/lev2/page1.md"), lev2page1)
            self.assertEqual(lev1page1.resolve_path("/lev1/lev2/page1"), lev2page1)
            self.assertEqual(lev1page1.resolve_path("lev2/page1.md"), lev2page1)
            self.assertEqual(lev1page1.resolve_path("lev2/page1"), lev2page1)

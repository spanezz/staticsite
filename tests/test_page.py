from __future__ import annotations

from unittest import TestCase

from . import utils as test_utils


class TestPage(test_utils.MockSiteTestMixin, TestCase):
    def test_resolve_path(self):
        files = {
            "toplevel.md": {},
            "lev1/page1.md": {},
            "lev1/page2.md": {},
            "lev1/lev2/page1.md": {},
        }
        with self.site(files) as mocksite:
            toplevel, lev1page1, lev1page2, lev2page1 = mocksite.page(
                    "toplevel", "lev1/page1", "lev1/page2", "lev1/lev2/page1")

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

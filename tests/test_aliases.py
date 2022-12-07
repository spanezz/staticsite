from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils


class TestAliases(test_utils.MockSiteTestMixin, TestCase):
    def test_site(self):
        files = {
            "page.md": {"aliases": ["alias", "test/alias"]},
        }
        with self.site(files) as mocksite:
            page, alias1, alias2 = mocksite.page("page", "alias", "test/alias")

            self.assertEqual(page.node.compute_path(), "page")
            self.assertEqual(page.build_path, "page/index.html")
            self.assertIn("aliases", page.meta)

            self.assertEqual(alias1.node.compute_path(), "alias")
            self.assertEqual(alias1.build_path, "alias/index.html")
            self.assertEqual(alias1.meta["template"], "redirect.html")
            self.assertEqual(alias1.meta["page"], page)
            self.assertNotIn("aliases", alias1.meta)

            self.assertEqual(alias2.node.compute_path(), "test/alias")
            self.assertEqual(alias2.build_path, "test/alias/index.html")
            self.assertEqual(alias2.meta["template"], "redirect.html")
            self.assertNotIn("aliases", alias2.meta)

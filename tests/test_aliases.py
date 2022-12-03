from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils


class TestAliases(TestCase):
    def test_site(self):
        files = {
            "page.md": {"aliases": ["alias", "test/alias"]},
        }
        with test_utils.workdir(files) as root:
            site = test_utils.Site(CONTENT=root)
            site.load()
            site.analyze()

            page = site.find_page("page")
            alias1 = site.find_page("alias")
            alias2 = site.find_page("test/alias")

            self.assertEqual(page.node.compute_path(), "page")
            self.assertEqual(page.build_node.compute_path(), "page/index.html")
            self.assertIn("aliases", page.meta)

            self.assertEqual(alias1.node.compute_path(), "alias")
            self.assertEqual(alias1.build_node.compute_path(), "alias/index.html")
            self.assertEqual(alias1.meta["template"], "redirect.html")
            self.assertEqual(alias1.meta["page"], page)
            self.assertNotIn("aliases", alias1.meta)

            self.assertEqual(alias2.node.compute_path(), "test/alias")
            self.assertEqual(alias2.build_node.compute_path(), "test/alias/index.html")
            self.assertEqual(alias2.meta["template"], "redirect.html")
            self.assertNotIn("aliases", alias2.meta)

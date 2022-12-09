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
            self.assertIsNotNone(page.aliases)

            self.assertEqual(alias1.node.compute_path(), "alias")
            self.assertEqual(alias1.build_path, "alias/index.html")
            self.assertEqual(alias1.template, "redirect.html")
            self.assertEqual(alias1.page, page)
            self.assertIsNone(alias1.aliases)

            self.assertEqual(alias2.node.compute_path(), "test/alias")
            self.assertEqual(alias2.build_path, "test/alias/index.html")
            self.assertEqual(alias2.template, "redirect.html")
            self.assertIsNone(alias2.aliases)

    def test_conflict(self):
        files = {
            "page.md": {"aliases": ["alias", "/page", "/dir1/dir2/alias"]},
        }
        with self.site(files, auto_load_site=False) as mocksite:
            with self.assertLogs(level="WARNING") as out:
                mocksite.load_site()
            self.assertEqual(out.output, ["WARNING:aliases:markdown:page.md defines alias '/page' pointing to itself"])
            mocksite.assertPagePaths(("", "page", "alias", "dir1/dir2/alias"))
            page, alias, alias1 = mocksite.page("page", "alias", "dir1/dir2/alias")

            self.assertEqual(page.TYPE, "markdown")
            self.assertEqual(page.node.compute_path(), "page")
            self.assertEqual(page.build_path, "page/index.html")
            self.assertEqual(page.aliases, ["alias", "/page", "/dir1/dir2/alias"])

            self.assertEqual(alias.node.compute_path(), "alias")
            self.assertEqual(alias.build_path, "alias/index.html")
            self.assertEqual(alias.template, "redirect.html")
            self.assertEqual(alias.page, page)
            self.assertIsNone(alias.aliases)
            mocksite.assertBuilt(None, "alias", "alias/index.html", sample="href=\"/page")

            self.assertEqual(alias1.node.compute_path(), "dir1/dir2/alias")
            self.assertEqual(alias1.build_path, "dir1/dir2/alias/index.html")
            self.assertEqual(alias1.template, "redirect.html")
            self.assertEqual(alias1.page, page)
            self.assertIsNone(alias.aliases)
            mocksite.assertBuilt(None, "dir1/dir2/alias", "dir1/dir2/alias/index.html", sample="href=\"/page")

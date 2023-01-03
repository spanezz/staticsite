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
            index, toplevel, lev1page1, lev1page2, lev2page1 = mocksite.page(
                    "", "toplevel", "lev1/page1", "lev1/page2", "lev1/lev2/page1")

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

            self.assertEqual(lev1page1.resolve_path("/"), index)

    def test_meta(self):
        files = {
            "index.md": {"title": "test"},
        }
        with self.site(files) as mocksite:
            index = mocksite.page("")
            # Direct field access
            self.assertEqual(index.title, "test")
            self.assertEqual(index.front_matter, {"title": "test"})

            # Dict-like field access via page.meta
            self.assertIn("title", index.meta)
            self.assertNotIn("test", index.meta)
            # Internal fields are hidden
            self.assertNotIn("front_matter", index.meta)

            self.assertEqual(index.meta["title"], "test")
            self.assertEqual(index.meta.get("title"), "test")

            with self.assertRaises(KeyError):
                index.meta["test"]
            self.assertIsNone(index.meta.get("test"))

            with self.assertRaises(KeyError):
                index.meta["front_matter"]
            self.assertIsNone(index.meta.get("front_matter"))

    def test_iter_pages(self):
        files = {
            "index.md": {},
            "index.txt": "",
            "tags.taxonomy": {},
            "lev1/page1.md": {"tags": ["a"]},
        }
        with self.site(files) as mocksite:
            index, asset, tags, tag_a, lev1, lev1page1, = mocksite.page(
                    "", "index.txt", "tags", "tags/a", "lev1", "lev1/page1")
            rss, atom, archive = mocksite.page("tags/a/index.rss", "tags/a/index.atom", "tags/a/archive")

            # Full iteration
            assets = []
            pages = []
            for page in mocksite.site.iter_pages():
                if page.TYPE == "asset":
                    assets.append(page)
                else:
                    pages.append(page)
            self.assertGreaterEqual(len(assets), 10)
            self.assertCountEqual(pages, [index, tags, tag_a, lev1, lev1page1, rss, atom, archive])

            # Skip static
            assets = []
            pages = []
            for page in mocksite.site.iter_pages(static=False):
                if page.TYPE == "asset":
                    assets.append(page)
                else:
                    pages.append(page)
            self.assertCountEqual(assets, [asset])
            self.assertCountEqual(pages, [index, tags, tag_a, lev1, lev1page1, rss, atom, archive])

            # Only source pages
            assets = []
            pages = []
            for page in mocksite.site.iter_pages(static=False, source_only=True):
                if page.TYPE == "asset":
                    assets.append(page)
                else:
                    pages.append(page)
            self.assertCountEqual(assets, [asset])
            self.assertCountEqual(pages, [index, tags, lev1, lev1page1])

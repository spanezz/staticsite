from __future__ import annotations

import os
from unittest import TestCase

from . import utils as test_utils


class TestDemo(test_utils.SiteTestMixin, TestCase):
    site_name = "demo"
    site_settings = {"SITE_AUTHOR": "Test User"}

    @test_utils.assert_no_logs()
    def test_meta(self):
        page = self.site.find_page("")
        self.assertEqual(page.site_path, "")
        self.assertEqual(page.meta["site_name"], "Example web site")
        self.assertEqual(page.meta["site_url"], "https://www.example.org")
        self.assertEqual(page.meta["author"], "Example author")

        page = self.site.find_page("blog")
        self.assertEqual(page.site_path, "blog")
        self.assertEqual(page.meta["site_name"], "Example web site")
        self.assertEqual(page.meta["site_url"], "https://www.example.org")
        self.assertEqual(page.meta["author"], "Example author")

    @test_utils.assert_no_logs()
    def test_dots(self):
        output = os.path.join(self.build_root, "index.html")
        self.assertTrue(os.path.exists(output))
        output = os.path.join(self.build_root, ".secret")
        self.assertFalse(os.path.exists(output))
        output = os.path.join(self.build_root, ".secrets")
        self.assertFalse(os.path.exists(output))

    @test_utils.assert_no_logs()
    def test_render_paths(self):
        self.assertBuilt("index.html", "", "index.html")
        self.assertBuilt("pages/README.md", "pages", "pages/index.html")
        self.assertBuilt("pages/doc/sub.md", "pages/doc/sub", "pages/doc/sub/index.html")

    @test_utils.assert_no_logs()
    def test_different_links(self):
        # Check rendered pages
        page = self.site.find_page("pages")
        self.assertEqual(page.body_start, ['Link: [Docs](doc/sub.md)', '', '[Back home](..)'])

        output = os.path.join(self.build_root, "pages/index.html")
        with open(output, "rt", encoding="utf8") as fd:
            content = fd.read()
        self.assertIn('<a href="/pages/doc/sub">Docs</a>', content)
        self.assertIn('<a href="/">Back home</a>', content)

        output = os.path.join(self.build_root, "pages/doc/sub/index.html")
        with open(output, "rt", encoding="utf8") as fd:
            content = fd.read()
        self.assertIn('<a href="/pages">Back to README</a>', content)

    def test_titles(self):
        self.maxDiff = None
        page = self.site.find_page("tags/example")
        self.assertIsNotNone(page.meta["template_title"])
        self.assertEqual(page.meta["title"], "Latest posts for tag <strong>example</strong>")

        self.assertEqual(self.site.find_page("blog/index.rss").to_dict(), {
            'site_path': 'blog/index.rss',
            "build_path": "blog/index.rss",
            "meta": {
                'atom_page': 'AtomPage(blog/index.atom)',
                "date": '2016-04-16 10:23:00+02:00',
                "draft": False,
                'index': 'J2Page(blog)',
                'author': "Example author",
                'copyright': '© 2016 Example author',
                'created_from': 'J2Page(blog)',
                'indexed': False,
                'syndicated': False,
                'pages': ['RstPage(blog/2016/rst_example)',
                          'MarkdownPage(blog/2016/example-series3)',
                          'MarkdownPage(blog/2016/example-series2)',
                          'MarkdownPage(blog/2016/example-series1)',
                          'MarkdownPage(blog/2016/example)'],
                'rss_page': 'RSSPage(blog/index.rss)',
                'site_name': 'Example web site',
                'site_url': 'https://www.example.org',
                'template': 'syndication.rss',
                'title': 'Example blog feed',
                'related': {},
            },
            "type": "rss",
        })

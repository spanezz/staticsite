from unittest import TestCase
from . import utils as test_utils
import os


class TestSite(TestCase):
    def test_titles(self):
        self.maxDiff = None
        with test_utils.example_site("demo") as site:
            page = site.pages["tags/example"]
            self.assertIsNotNone(page.meta["template_title"])
            self.assertEqual(page.meta["title"], "Latest posts for tag <strong>example</strong>")

            self.assertEqual(site.pages["blog/index.rss"].to_dict(), {
                "src": {
                    "relpath": "blog/index.html",
                    "abspath": os.path.join(site.content_root, "blog/index.html"),
                },
                'site_path': 'blog/index.rss',
                "build_path": "blog/index.rss",
                "meta": {
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
                    'site_name': 'Example web site',
                    'site_url': 'https://www.example.org',
                    'template': 'syndication.rss',
                    'title': 'Example blog feed',
                    'related': {},
                },
                "type": "rss",
            })

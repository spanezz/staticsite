from unittest import TestCase
from . import utils as test_utils
import os


class TestSite(TestCase):
    def test_meta(self):
        self.maxDiff = None

        with test_utils.example_site("blog", SITE_AUTHOR="Test User") as site:
            page = site.pages["/about"]
            self.assertEqual(page.meta["title"], "About")

            self.assertEqual(site.pages["/about"].to_dict(), {
                "src": {
                    "relpath": "about.md",
                    "abspath": os.path.join(site.content_root, "about.md"),
                },
                "meta": {
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': True,
                    'syndicated': True,
                    "syndication_date": '2019-06-01 12:30:00+02:00',
                    'site_name': 'My example blog',
                    'site_path': '/about',
                    'site_url': 'https://www.example.org',
                    "build_path": "about/index.html",
                    'template': 'page.html',
                    'title': 'About',
                    'nav': ['MarkdownPage(/)', 'MarkdownPage(/about)'],
                    'nav_title': 'About',
                },
                "type": "markdown",
            })

            self.assertEqual(site.pages["/"].to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                "meta": {
                    "date": '2019-12-30 17:30:00+01:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': True,
                    'syndicated': True,
                    'syndication': {'atom_page': 'AtomPage(/index.atom)',
                                    'index': 'MarkdownPage(/)',
                                    'pages': ['MarkdownPage(/posts/example)'],
                                    'rss_page': 'RSSPage(/index.rss)'},
                    'syndication_date': '2019-06-01 12:30:00+02:00',
                    'pages': ['MarkdownPage(/posts/example)'],
                    'site_name': 'My example blog',
                    'site_path': '/',
                    'site_url': 'https://www.example.org',
                    "build_path": "index.html",
                    'template': 'blog.html',
                    'title': 'My example blog',
                    'nav': ['MarkdownPage(/)', 'MarkdownPage(/about)'],
                    'nav_title': 'My example blog',
                },
                "type": "markdown",
            })

            self.assertEqual(site.pages["/archive"].to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                "meta": {
                    "date": '2019-12-30 17:30:00+01:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'pages': ['MarkdownPage(/posts/example)'],
                    'site_name': 'My example blog',
                    'site_path': '/archive',
                    'site_url': 'https://www.example.org',
                    "build_path": "archive/index.html",
                    'template': 'archive.html',
                    'title': 'My example blog',
                    'nav': ['MarkdownPage(/)', 'MarkdownPage(/about)'],
                },
                "type": "archive",
            })

            self.assertEqual(site.pages["/index.rss"].to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                "meta": {
                    "date": '2019-12-30 17:30:00+01:00',
                    "draft": False,
                    'index': 'MarkdownPage(/)',
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'pages': ['MarkdownPage(/posts/example)'],
                    'site_name': 'My example blog',
                    'site_path': '/index.rss',
                    'site_url': 'https://www.example.org',
                    "build_path": "index.rss",
                    'template': 'syndication.rss',
                    'title': 'My example blog',
                    'nav': ['MarkdownPage(/)', 'MarkdownPage(/about)'],
                },
                "type": "rss",
            })

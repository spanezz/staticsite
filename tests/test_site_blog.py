from unittest import TestCase
from . import utils as test_utils
import datetime
import os


class TestSite(TestCase):
    def test_meta(self):
        self.maxDiff = None

        with test_utils.example_site("blog", SITE_AUTHOR="Test User") as site:
            test_time = datetime.datetime(2020, 1, 2, 12, 00, tzinfo=site.timezone)
            for page in site.pages.values():
                page.meta["date"] = test_time
                if "syndication_date" in page.meta:
                    page.meta["syndication_date"] = test_time

            page = site.pages["/about"]
            self.assertEqual(page.meta["title"], "About")

            self.assertEqual(site.pages["/about"].to_dict(), {
                "src": {
                    "relpath": "about.md",
                    "abspath": os.path.join(site.content_root, "about.md"),
                },
                "meta": {
                    "date": '2020-01-02 12:00:00+01:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2020 Test User',
                    'indexed': True,
                    'syndicated': True,
                    "syndication_date": '2020-01-02 12:00:00+01:00',
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

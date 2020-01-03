from unittest import TestCase
import os
import datetime
from . import utils as test_utils


class TestNav(TestCase):
    """
    Test metadata collected on site load
    """
    def test_dir(self):
        self.maxDiff = None

        files = {
            "index.md": {"nav": ["about.md"]},
            "about.md": {},
            "dir1/dir2/dir3/page.md": {},
        }

        with test_utils.testsite(files) as site:
            test_time = datetime.datetime(2020, 1, 2, 12, 00, tzinfo=site.timezone)
            for page in site.pages.values():
                page.meta["date"] = test_time
                if "syndication_date" in page.meta:
                    page.meta["syndication_date"] = test_time

            page = site.pages["/dir1/dir2/dir3/page"]
            self.assertEqual(page.to_dict(), {
                "src": {
                    "relpath": "dir1/dir2/dir3/page.md",
                    "abspath": os.path.join(site.content_root, "dir1/dir2/dir3/page.md"),
                },
                "meta": {
                    "author": "Test User",
                    "copyright": '© 2020 Test User',
                    "date": '2020-01-02 12:00:00+01:00',
                    "draft": False,
                    'indexed': True,
                    'nav': ["MarkdownPage(/about)"],
                    'syndicated': True,
                    "syndication_date": '2020-01-02 12:00:00+01:00',
                    'site_name': 'Test site',
                    'site_path': '/dir1/dir2/dir3/page',
                    'site_url': 'https://www.example.org',
                    "build_path": "dir1/dir2/dir3/page/index.html",
                    'template': 'page.html',
                    'title': 'Test site',
                },
                "type": "markdown",
            })

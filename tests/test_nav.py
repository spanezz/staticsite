from unittest import TestCase
import os
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
            page = site.pages["/dir1/dir2/dir3/page"]
            self.assertEqual(page.to_dict(), {
                "src": {
                    "relpath": "dir1/dir2/dir3/page.md",
                    "abspath": os.path.join(site.content_root, "dir1/dir2/dir3/page.md"),
                },
                "build_path": "dir1/dir2/dir3/page/index.html",
                "meta": {
                    "author": "Test User",
                    "copyright": '© 2019 Test User',
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'indexed': True,
                    'nav': ["MarkdownPage(/about)"],
                    'syndicated': True,
                    "syndication_date": '2019-06-01 12:30:00+02:00',
                    'site_name': 'Test site',
                    'site_path': '/dir1/dir2/dir3/page',
                    'site_url': 'https://www.example.org',
                    'template': 'page.html',
                    'title': 'Test site',
                    'related': {},
                },
                "type": "markdown",
            })

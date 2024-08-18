import os
from unittest import TestCase

from . import utils as test_utils


class TestNav(test_utils.MockSiteTestMixin, TestCase):
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

        with self.site(files) as mocksite:
            page = mocksite.page("dir1/dir2/dir3/page")
            self.assertEqual(
                page.to_dict(),
                {
                    "src": {
                        "relpath": "dir1/dir2/dir3/page.md",
                        "abspath": os.path.join(
                            mocksite.site.content_root, "dir1/dir2/dir3/page.md"
                        ),
                    },
                    "build_path": "dir1/dir2/dir3/page/index.html",
                    "site_path": "dir1/dir2/dir3/page",
                    "meta": {
                        "author": "Test User",
                        "copyright": "© 2019 Test User",
                        "date": "2019-06-01 12:30:00+02:00",
                        "draft": False,
                        "indexed": True,
                        "nav": ["MarkdownPage(about)"],
                        "syndicated": True,
                        "syndication_date": "2019-06-01 12:30:00+02:00",
                        "site_name": "Test site",
                        "site_url": "https://www.example.org",
                        "template": "page.html",
                        "template_copyright": "compiled:None",
                        "title": "Test site",
                        "related": {},
                    },
                    "type": "markdown",
                },
            )

from unittest import TestCase
import os
from . import utils as test_utils


class TestMetadata(test_utils.MockSiteTestMixin, TestCase):
    """
    Test metadata collected on site load
    """
    def test_dir(self):
        files = {
            ".staticsite": {
                "files": {
                    "*.html": {
                        "title": "Default title",
                    },
                    "test.html": {
                        "title": "Test title",
                    },
                },
            },
            "index.html": "",
            "test.html": "",
            "test1.html": """
{% block front_matter %}
---
title: Test1 title
{% endblock %}""",
        }

        with self.site(files) as mocksite:
            mocksite.assertPagePaths(("", "test.html", "test1.html"))
            index, test, test1 = mocksite.page("", "test.html", "test1.html")

            self.assertEqual(index.TYPE, "jinja2")
            self.assertEqual(test.TYPE, "jinja2")
            self.assertEqual(test1.TYPE, "jinja2")

            self.assertEqual(index.meta["title"], "Default title")
            self.assertEqual(test.meta["title"], "Test title")
            self.assertEqual(test1.meta["title"], "Test1 title")

    def test_tree_meta(self):
        files = {
            ".staticsite": {
                "site_name": "Root site",
            },
            "page.md": {},
            "page1.md": {"site_name": "Page 1 site"},
            "dir1/page.md": {},
            "dir1/dir2/.staticsite": {
                "site_name": "dir2 site",
            },
            "dir1/dir2/page.md": {},
        }

        with self.site(files) as mocksite:
            self.assertEqual(mocksite.page("").meta["site_name"], "Root site")
            self.assertEqual(mocksite.page("page").meta["site_name"], "Root site")
            self.assertEqual(mocksite.page("page1").meta["site_name"], "Page 1 site")
            self.assertEqual(mocksite.page("dir1").meta["site_name"], "Root site")
            self.assertEqual(mocksite.page("dir1/page").meta["site_name"], "Root site")
            self.assertEqual(mocksite.page("dir1/dir2").meta["site_name"], "dir2 site")
            self.assertEqual(mocksite.page("dir1/dir2/page").meta["site_name"], "dir2 site")

    def test_asset(self):
        self.maxDiff = None

        files = {
            ".staticsite": {
                "files": {
                    "test.md": {
                        "asset": True,
                    },
                },
            },
            "test.md": {},
            "test1.md": {},
        }

        with self.site(files) as mocksite:
            mocksite.assertPagePaths(("", "test.md", "test1"))
            index, test, test1 = mocksite.page("", "test.md", "test1")
            self.assertEqual(index.TYPE, "dir")
            self.assertEqual(test.TYPE, "asset")
            self.assertEqual(test1.TYPE, "markdown")

    def test_dir_asset(self):
        files = {
            ".staticsite": {
                "dirs": {
                    "examples": {
                        "asset": True,
                    },
                },
            },
            "test.md": {},
            "examples/test1.md": {},
            "examples/subdir/test2.md": {},
        }

        with self.site(files) as mocksite:
            mocksite.assertPagePaths(("", "test", "examples/test1.md", "examples/subdir/test2.md"))
            index, test, test1, test2 = mocksite.page("", "test", "examples/test1.md", "examples/subdir/test2.md")
            self.assertEqual(index.TYPE, "dir")
            self.assertEqual(test.TYPE, "markdown")
            self.assertEqual(test1.TYPE, "asset")
            self.assertEqual(test2.TYPE, "asset")


class TestSiteName(test_utils.MockSiteTestMixin, TestCase):
    def test_from_content_dir_name(self):
        sitedef = test_utils.MockSite({
            "index.md": {},
            "page.md": {},
            "dir/page.md": {},
        })
        sitedef.settings.SITE_NAME = None

        with self.site(sitedef) as mocksite:
            expected = os.path.basename(mocksite.root)
            self.assertEqual(mocksite.page("").meta["site_name"], expected)
            self.assertEqual(mocksite.page("page").meta["site_name"], expected)
            self.assertEqual(mocksite.page("dir/page").meta["site_name"], expected)

    def test_from_settings(self):
        sitedef = test_utils.MockSite({
            "index.md": {},
            "page.md": {},
            "dir/page.md": {},
        })
        sitedef.settings.SITE_NAME = "Site Name"

        with self.site(sitedef) as mocksite:
            self.assertEqual(mocksite.page("").meta["site_name"], "Site Name")
            self.assertEqual(mocksite.page("page").meta["site_name"], "Site Name")
            self.assertEqual(mocksite.page("dir/page").meta["site_name"], "Site Name")

    def test_from_dir_meta(self):
        files = {
            ".staticsite": {"site_name": "Site Name dirmeta"},
            "index.md": {},
            "page.md": {},
            "dir/page.md": {},
        }

        with self.site(files) as mocksite:
            self.assertEqual(mocksite.page("").meta["site_name"], "Site Name dirmeta")
            self.assertEqual(mocksite.page("page").meta["site_name"], "Site Name dirmeta")
            self.assertEqual(mocksite.page("dir/page").meta["site_name"], "Site Name dirmeta")

    def test_from_root_title(self):
        sitedef = test_utils.MockSite({
            "index.md": {"title": "Site Name title"},
            "page.md": {},
            "dir/page.md": {},
        })
        sitedef.settings.SITE_NAME = None

        with self.site(sitedef) as mocksite:
            self.assertEqual(mocksite.page("").meta["site_name"], "Site Name title")
            self.assertEqual(mocksite.page("page").meta["site_name"], "Site Name title")
            self.assertEqual(mocksite.page("dir/page").meta["site_name"], "Site Name title")


class TestFields(test_utils.MockSiteTestMixin, TestCase):
    def test_date(self):
        self.maxDiff = None

        sitedef = test_utils.MockSite({
            "index.html": """
{% block front_matter %}
---
title: Test1 title
date: 2000-01-01 00:00:00
{% endblock %}""",
            "page.md": """---
date: 2005-01-01 00:00:00
---
""",
            "page1.yaml": """---
data_type: test
date: 2010-01-01 00:00:00
""",
        })
        sitedef.settings.SITE_NAME = None
        sitedef.settings.TIMEZONE = "UTC"

        with self.site(sitedef) as mocksite:
            j2page, mdpage, datapage = mocksite.find_page("", "page", "page1")

            self.assertEqual(j2page.to_dict(), {
                "src": {
                    "relpath": "index.html",
                    "abspath": os.path.join(mocksite.root, "index.html"),
                },
                'site_path': '',
                "build_path": "index.html",
                "meta": {
                    "author": "Test User",
                    "copyright": '© 2000 Test User',
                    "date": '2000-01-01 00:00:00+00:00',
                    "draft": False,
                    'indexed': True,
                    'syndicated': True,
                    "syndication_date": '2000-01-01 00:00:00+00:00',
                    'site_name': 'Test1 title',
                    'site_url': 'https://www.example.org',
                    'site_path': '/',
                    'template': 'compiled:index.html',
                    'template_copyright': 'compiled:None',
                    'title': 'Test1 title',
                    'related': {},
                },
                "type": "jinja2",
            })

            self.assertEqual(mdpage.to_dict(), {
                "src": {
                    "relpath": "page.md",
                    "abspath": os.path.join(mocksite.root, "page.md"),
                },
                'site_path': 'page',
                "build_path": "page/index.html",
                "meta": {
                    "author": "Test User",
                    "copyright": '© 2005 Test User',
                    "date": '2005-01-01 00:00:00+00:00',
                    "draft": False,
                    'indexed': True,
                    'syndicated': True,
                    "syndication_date": '2005-01-01 00:00:00+00:00',
                    'site_name': 'Test1 title',
                    'site_url': 'https://www.example.org',
                    'template': 'page.html',
                    'title': 'Test1 title',
                    'related': {},
                },
                "type": "markdown",
            })

            self.assertEqual(datapage.to_dict(), {
                "src": {
                    "relpath": "page1.yaml",
                    "abspath": os.path.join(mocksite.root, "page1.yaml"),
                },
                'site_path': 'page1',
                "build_path": "page1/index.html",
                "meta": {
                    "author": "Test User",
                    "copyright": '© 2010 Test User',
                    "date": '2010-01-01 00:00:00+00:00',
                    "draft": False,
                    'indexed': True,
                    'syndicated': True,
                    "syndication_date": '2010-01-01 00:00:00+00:00',
                    'site_name': 'Test1 title',
                    'site_url': 'https://www.example.org',
                    'template': 'compiled:data.html',
                    'title': 'Test1 title',
                    'data_type': 'test',
                    'related': {},
                },
                "type": "data",
            })

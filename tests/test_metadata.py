from unittest import TestCase
import os
from . import utils as test_utils


class TestMetadata(TestCase):
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

        with test_utils.testsite(files) as site:
            self.assertCountEqual([k for k in site.pages.keys() if not k.startswith("static/")], [
                "", "test.html", "test1.html"
            ])

            index = site.pages[""]
            test = site.pages["test.html"]
            test1 = site.pages["test1.html"]

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

        with test_utils.workdir(files) as root:
            site = test_utils.Site(PROJECT_ROOT=root)
            site.load()
            site.analyze()

            self.assertEqual(site.pages[""].meta["site_name"], "Root site")
            self.assertEqual(site.pages["page"].meta["site_name"], "Root site")
            self.assertEqual(site.pages["page1"].meta["site_name"], "Page 1 site")
            self.assertEqual(site.pages["dir1"].meta["site_name"], "Root site")
            self.assertEqual(site.pages["dir1/page"].meta["site_name"], "Root site")
            self.assertEqual(site.pages["dir1/dir2"].meta["site_name"], "dir2 site")
            self.assertEqual(site.pages["dir1/dir2/page"].meta["site_name"], "dir2 site")

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

        with test_utils.workdir(files) as root:
            site = test_utils.Site(CONTENT=root)
            site.load()
            site.analyze()

            self.assertCountEqual([k for k in site.pages.keys() if not k.startswith("static/")], [
                "", "test.md", "test1",
            ])

            index = site.pages[""]
            test = site.pages["test.md"]
            test1 = site.pages["test1"]

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

        with test_utils.workdir(files) as root:
            site = test_utils.Site(CONTENT=root)
            site.load()
            site.analyze()

            self.assertCountEqual([k for k in site.pages.keys() if not k.startswith("static/")], [
                "", "test",
                "examples/test1.md",
                "examples/subdir/test2.md",
            ])

            index = site.pages[""]
            test = site.pages["test"]
            test1 = site.pages["examples/test1.md"]
            test2 = site.pages["examples/subdir/test2.md"]

            self.assertEqual(index.TYPE, "dir")
            self.assertEqual(test.TYPE, "markdown")
            self.assertEqual(test1.TYPE, "asset")
            self.assertEqual(test2.TYPE, "asset")


class TestSiteName(TestCase):
    def test_from_content_dir_name(self):
        files = {
            "index.md": {},
            "page.md": {},
            "dir/page.md": {},
        }

        with test_utils.workdir(files) as root:
            site = test_utils.Site(SITE_NAME=None, CONTENT=root)
            site.load()
            site.analyze()

            expected = os.path.basename(root)

            self.assertEqual(site.pages[""].meta["site_name"], expected)
            self.assertEqual(site.pages["page"].meta["site_name"], expected)
            self.assertEqual(site.pages["dir/page"].meta["site_name"], expected)

    def test_from_settings(self):
        files = {
            "index.md": {},
            "page.md": {},
            "dir/page.md": {},
        }

        with test_utils.workdir(files) as root:
            # Site name from settings
            site = test_utils.Site(SITE_NAME="Site Name", CONTENT=root)
            site.load()
            site.analyze()

            self.assertEqual(site.pages[""].meta["site_name"], "Site Name")
            self.assertEqual(site.pages["page"].meta["site_name"], "Site Name")
            self.assertEqual(site.pages["dir/page"].meta["site_name"], "Site Name")

    def test_from_dir_meta(self):
        files = {
            ".staticsite": {"site_name": "Site Name dirmeta"},
            "index.md": {},
            "page.md": {},
            "dir/page.md": {},
        }

        with test_utils.workdir(files) as root:
            site = test_utils.Site(CONTENT=root)
            site.load()
            site.analyze()

            self.assertEqual(site.pages[""].meta["site_name"], "Site Name dirmeta")
            self.assertEqual(site.pages["page"].meta["site_name"], "Site Name dirmeta")
            self.assertEqual(site.pages["dir/page"].meta["site_name"], "Site Name dirmeta")

    def test_from_root_title(self):
        files = {
            "index.md": {"title": "Site Name title"},
            "page.md": {},
            "dir/page.md": {},
        }

        with test_utils.workdir(files) as root:
            site = test_utils.Site(SITE_NAME=None, CONTENT=root)
            site.load()
            site.analyze()

            self.assertEqual(site.pages[""].meta["site_name"], "Site Name title")
            self.assertEqual(site.pages["page"].meta["site_name"], "Site Name title")
            self.assertEqual(site.pages["dir/page"].meta["site_name"], "Site Name title")


class TestFields(TestCase):
    def test_date(self):
        self.maxDiff = None

        files = {
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
        }

        with test_utils.workdir(files) as root:
            site = test_utils.Site(SITE_NAME=None, CONTENT=root, TIMEZONE="UTC")
            site.load()
            site.analyze()

            j2page = site.pages[""]
            mdpage = site.pages["page"]
            datapage = site.pages["page1"]

            self.assertEqual(j2page.to_dict(), {
                "src": {
                    "relpath": "index.html",
                    "abspath": os.path.join(root, "index.html"),
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
                    'template': 'compiled:index.html',
                    'title': 'Test1 title',
                    'related': {},
                },
                "type": "jinja2",
            })

            self.assertEqual(mdpage.to_dict(), {
                "src": {
                    "relpath": "page.md",
                    "abspath": os.path.join(root, "page.md"),
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
                    "abspath": os.path.join(root, "page1.yaml"),
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

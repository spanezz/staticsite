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

        with test_utils.workdir(files) as root:
            site = test_utils.Site(PROJECT_ROOT=root)
            site.load()
            site.analyze()

            self.assertCountEqual(site.pages.keys(), [
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
            site = test_utils.Site()
            site.load(content_root=root)
            site.analyze()

            self.assertCountEqual(site.pages.keys(), [
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
            site = test_utils.Site()
            site.load(content_root=root)
            site.analyze()

            self.assertCountEqual(site.pages.keys(), [
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
            site = test_utils.Site(SITE_NAME=None)
            site.load(content_root=root)
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
            site = test_utils.Site(SITE_NAME="Site Name")
            site.load(content_root=root)
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
            site = test_utils.Site()
            site.load(content_root=root)
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
            site = test_utils.Site(SITE_NAME=None)
            site.load(content_root=root)
            site.analyze()

            self.assertEqual(site.pages[""].meta["site_name"], "Site Name title")
            self.assertEqual(site.pages["page"].meta["site_name"], "Site Name title")
            self.assertEqual(site.pages["dir/page"].meta["site_name"], "Site Name title")

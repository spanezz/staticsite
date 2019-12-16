from unittest import TestCase
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

from unittest import TestCase
from . import utils as test_utils


class MockContext:
    def __init__(self, **kw):
        self.parent = kw
        self.name = "test"


class TestUrlFor(TestCase):
    """
    Test theme functions
    """
    def test_no_site_root(self):
        files = {
            ".staticsite": {
                "site": {
                    "site_url": "https://www.example.org",
                },
            },
            "page1.md": {},
            "dir/page2.md": {},
            "dir/index.html": {},
        }

        with test_utils.workdir(files) as root:
            site = test_utils.Site(PROJECT_ROOT=root)
            site.load()
            site.analyze()

            def url_for(dest, parent=None, **kw):
                if parent:
                    context = MockContext(page=parent)
                else:
                    context = None
                return site.theme.jinja2_url_for(context, dest, **kw)

            parent = site.pages[""]
            self.assertEqual(url_for("page1.md", parent=parent), "/page1")
            self.assertEqual(url_for("page1", parent=parent), "/page1")

            # Autogenerated index.html do not exist in sources or link
            # namespaces, and do not resolve, even if they would be written on
            # disk
            with self.assertLogs(level="WARN") as out:
                self.assertEqual(url_for("page1/index.html", parent=parent), "")
            self.assertEqual(len(out.output), 1)
            self.assertIn("url_for: cannot resolve `page1/index.html` relative to ``", out.output[0])

            # index.html however resolve, as they exist in the sources
            # namespace
            self.assertEqual(url_for("dir", parent=parent), "/dir")
            self.assertEqual(url_for("dir/index.html", parent=parent), "/dir")

            # Test absolute urls
            self.assertEqual(url_for("page1", parent=parent, absolute=True), "https://www.example.org/page1")

    def test_site_root(self):
        files = {
            ".staticsite": {
                "site": {
                    "site_url": "https://www.example.org",
                    "site_root": "prefix",
                },
            },
            "page1.md": {},
            "dir/page2.md": {},
            "dir/index.html": {},
        }

        with test_utils.workdir(files) as root:
            site = test_utils.Site(PROJECT_ROOT=root)
            site.load()
            site.analyze()

            def url_for(dest, parent=None, **kw):
                if parent:
                    context = MockContext(page=parent)
                else:
                    context = None
                return site.theme.jinja2_url_for(context, dest, **kw)

            parent = site.pages[""]
            self.assertEqual(url_for("page1.md", parent=parent), "/prefix/page1")
            self.assertEqual(url_for("page1", parent=parent), "/prefix/page1")

            # Test absolute urls
            self.assertEqual(url_for("page1", parent=parent, absolute=True), "https://www.example.org/prefix/page1")
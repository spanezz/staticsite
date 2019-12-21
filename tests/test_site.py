from unittest import TestCase
from staticsite.cmd.build import Build
from staticsite.settings import Settings
from staticsite import Site
from . import utils as test_utils
import os


class TestSite(TestCase):
    def test_meta(self):
        with test_utils.assert_no_logs():
            with test_utils.example_site() as root:
                settings = Settings()
                settings.load(os.path.join(root, "settings.py"))
                if settings.PROJECT_ROOT is None:
                    settings.PROJECT_ROOT = root
                site = Site(settings=settings)
                site.load()
                site.analyze()

                page = site.pages[""]
                self.assertEqual(page.meta["site_name"], "Example web site")
                self.assertEqual(page.meta["site_url"], "https://www.example.org")
                self.assertEqual(page.meta["site_root"], "/")
                self.assertEqual(page.meta["author"], "Example author")

                page = site.pages["blog"]
                self.assertEqual(page.meta["site_name"], "Example web site")
                self.assertEqual(page.meta["site_url"], "https://www.example.org")
                self.assertEqual(page.meta["site_root"], "/")
                self.assertEqual(page.meta["author"], "Example author")


class TestBuild(TestCase):
    def test_dots(self):
        with test_utils.assert_no_logs():
            with test_utils.example_site() as root:
                args = test_utils.Args(project=root)
                build = Build(args)
                build.run()

                output = os.path.join(root, "web/.secret")
                self.assertFalse(os.path.exists(output))
                output = os.path.join(root, "web/.secrets")
                self.assertFalse(os.path.exists(output))

    def test_different_links(self):
        with test_utils.assert_no_logs():
            with test_utils.example_site() as root:
                args = test_utils.Args(project=root)
                build = Build(args)
                build.run()

                output = os.path.join(root, "web/pages/index.html")
                with open(output, "rt") as fd:
                    content = fd.read()
                self.assertIn('<a href="/pages/doc/sub">Docs</a>', content)
                self.assertIn('<a href="/">Back home</a>', content)

                output = os.path.join(root, "web/pages/doc/sub/index.html")
                with open(output, "rt") as fd:
                    content = fd.read()
                self.assertIn('<a href="/pages">Back to README</a>', content)

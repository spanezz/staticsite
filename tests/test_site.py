from unittest import TestCase
from staticsite.cmd.build import Build
from . import utils as test_utils
import os


class TestSite(TestCase):
    def test_meta(self):
        with test_utils.assert_no_logs():
            with test_utils.example_site() as site:
                page = site.pages[""]
                self.assertEqual(page.site_path, "")
                self.assertEqual(page.meta["site_name"], "Example web site")
                self.assertEqual(page.meta["site_url"], "https://www.example.org")
                self.assertEqual(page.meta["author"], "Example author")

                page = site.pages["blog"]
                self.assertEqual(page.site_path, "blog")
                self.assertEqual(page.meta["site_name"], "Example web site")
                self.assertEqual(page.meta["site_url"], "https://www.example.org")
                self.assertEqual(page.meta["author"], "Example author")


class TestBuild(TestCase):
    def test_dots(self):
        with test_utils.assert_no_logs():
            with test_utils.example_site_dir() as root:
                args = test_utils.Args(project=root)
                build = Build(args)
                build.settings.THEME_PATHS.insert(0, os.path.join(os.getcwd(), "themes"))
                build.run()

                output = os.path.join(root, "web/.secret")
                self.assertFalse(os.path.exists(output))
                output = os.path.join(root, "web/.secrets")
                self.assertFalse(os.path.exists(output))

    def test_different_links(self):
        with test_utils.assert_no_logs():
            with test_utils.example_site_dir() as root:
                args = test_utils.Args(project=root)
                build = Build(args)
                build.settings.THEME_PATHS.insert(0, os.path.join(os.getcwd(), "themes"))
                build.run()

                output = os.path.join(root, "web/pages/index.html")
                with open(output, "rt", encoding="utf8") as fd:
                    content = fd.read()
                self.assertIn('<a href="/pages/doc/sub">Docs</a>', content)
                self.assertIn('<a href="/">Back home</a>', content)

                output = os.path.join(root, "web/pages/doc/sub/index.html")
                with open(output, "rt", encoding="utf8") as fd:
                    content = fd.read()
                self.assertIn('<a href="/pages">Back to README</a>', content)

from unittest import TestCase
from staticsite.cmd.build import Build
from staticsite import Site
from . import utils as test_utils
from contextlib import contextmanager
import os


@contextmanager
def example_site(name="demo"):
    with test_utils.assert_no_logs():
        with test_utils.example_site(name) as root:
            settings = test_utils.TestSettings()
            settings.load(os.path.join(root, "settings.py"))
            if settings.PROJECT_ROOT is None:
                settings.PROJECT_ROOT = root
            site = Site(settings=settings)
            site.load()
            site.analyze()
            yield site


class TestSite(TestCase):
    def test_titles(self):
        with example_site("demo") as site:
            page = site.pages["tags/example"]
            self.assertIsNotNone(page.meta["template_title"])
            self.assertEqual(page.meta["title"], "Latest posts for tag <strong>example</strong>")

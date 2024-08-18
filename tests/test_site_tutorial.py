from __future__ import annotations

import os
from unittest import TestCase

from staticsite.cmd.build import Builder
from staticsite.site import Path

from . import utils as test_utils


class TestTutorial(test_utils.SiteTestMixin, TestCase):
    site_name = "tutorial"
    site_settings = {"SITE_AUTHOR": "Test User"}

    @test_utils.assert_no_logs()
    def test_render_paths(self):
        self.assertBuilt("index.md", "", "index.html", sample="Welcome to my new blog")


class BuiltExampleSite(test_utils.ExampleSite):
    def populate_workdir(self):
        super().populate_workdir()
        # Build the site inside the workdir
        site = self.create_site()
        site.settings.OUTPUT = os.path.join(self.root, "built_site")
        overrides = {"st_mtime": self.mock_file_mtime}
        with test_utils.mock_file_stat(overrides):
            site.load()
        builder = Builder(site)
        builder.write()


class TestBuiltTutorial(test_utils.SiteTestMixin, TestCase):
    site_name = "tutorial"
    site_settings = {"SITE_AUTHOR": "Test User"}
    site_cls = BuiltExampleSite

    @test_utils.assert_no_logs()
    def test_built_marker(self):
        built_marker = os.path.join(self.mocksite.root, "built_site", ".staticsite")
        self.assertTrue(os.path.exists(built_marker))
        with open(built_marker) as fd:
            self.assertEqual(fd.read(), "---\nskip: yes\n")

    @test_utils.assert_no_logs()
    def test_render_paths(self):
        self.assertBuilt("index.md", "", "index.html", sample="Welcome to my new blog")
        self.assertIsNone(self.site.root.lookup_page(Path.from_string("/built_site/")))

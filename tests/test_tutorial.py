from __future__ import annotations

import os
from unittest import TestCase

from staticsite.cmd.build import Builder

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
        site.load()
        builder = Builder(site)
        builder.write()


class TestBuiltTutorial(test_utils.SiteTestMixin, TestCase):
    site_name = "tutorial"
    site_settings = {"SITE_AUTHOR": "Test User"}
    site_cls = BuiltExampleSite

    @test_utils.assert_no_logs()
    def test_render_paths(self):
        self.assertBuilt("index.md", "", "index.html", sample="Welcome to my new blog")

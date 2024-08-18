from __future__ import annotations

import os
from unittest import TestCase, mock

from staticsite.cmd.command import SiteCommand

from . import utils as test_utils


class TestBuildSettings(test_utils.MockSiteTestMixin, TestCase):
    """
    Test settings after command line parsing
    """

    def test_defaults(self):
        with self.site(test_utils.MockSite({}, auto_load_site=False)) as mocksite:
            with mock.patch("os.getcwd", return_value=mocksite.root):
                args = test_utils.Args()
                cmd = SiteCommand(args)
            settings = cmd.settings
            self.assertEqual(settings.PROJECT_ROOT, mocksite.root)
            self.assertEqual(settings.SITE_ROOT, "/")
            self.assertIsNone(settings.SITE_NAME)
            self.assertEqual(settings.ARCHETYPES, "archetypes")
            self.assertIsNone(settings.CONTENT)
            self.assertEqual(settings.THEME, "default")
            self.assertIsNone(settings.OUTPUT)
            self.assertIsNone(settings.TIMEZONE)
            self.assertEqual(settings.SYSTEM_ASSETS, [])
            self.assertFalse(settings.DRAFT_MODE)
            self.assertTrue(settings.CACHE_REBUILDS)

    def test_find_settings_py(self):
        files = {
            "settings.py": "SITE_NAME = 'Test Site'\n",
        }
        with self.site(test_utils.MockSite(files, auto_load_site=False)) as mocksite:
            with mock.patch("os.getcwd", return_value=mocksite.root):
                args = test_utils.Args()
                cmd = SiteCommand(args)
            settings = cmd.settings
            self.assertEqual(settings.PROJECT_ROOT, mocksite.root)
            self.assertEqual(settings.SITE_ROOT, "/")
            self.assertEqual(settings.SITE_NAME, "Test Site")
            self.assertEqual(settings.ARCHETYPES, "archetypes")
            self.assertIsNone(settings.CONTENT)
            self.assertEqual(settings.THEME, "default")
            self.assertIsNone(settings.OUTPUT)
            self.assertIsNone(settings.TIMEZONE)
            self.assertEqual(settings.SYSTEM_ASSETS, [])
            self.assertFalse(settings.DRAFT_MODE)
            self.assertTrue(settings.CACHE_REBUILDS)

    def test_find_dotstaticsite_py(self):
        files = {
            ".staticsite.py": "SITE_NAME = 'Test Site'\n",
        }
        with self.site(test_utils.MockSite(files, auto_load_site=False)) as mocksite:
            with mock.patch("os.getcwd", return_value=mocksite.root):
                args = test_utils.Args()
                cmd = SiteCommand(args)
            settings = cmd.settings
            self.assertEqual(settings.PROJECT_ROOT, mocksite.root)
            self.assertEqual(settings.SITE_ROOT, "/")
            self.assertEqual(settings.SITE_NAME, "Test Site")
            self.assertEqual(settings.ARCHETYPES, "archetypes")
            self.assertIsNone(settings.CONTENT)
            self.assertEqual(settings.THEME, "default")
            self.assertIsNone(settings.OUTPUT)
            self.assertIsNone(settings.TIMEZONE)
            self.assertEqual(settings.SYSTEM_ASSETS, [])
            self.assertFalse(settings.DRAFT_MODE)
            self.assertTrue(settings.CACHE_REBUILDS)


class TestExampleProject(test_utils.SiteTestMixin, TestCase):
    site_name = "demo"

    def test_settings(self):
        args = test_utils.Args(project=self.mocksite.root)
        cmd = SiteCommand(args)
        settings = cmd.settings
        self.assertEqual(settings.PROJECT_ROOT, self.mocksite.root)
        self.assertEqual(settings.SITE_ROOT, "/")
        # self.assertEqual(settings.SITE_NAME, "Example web site")
        self.assertIsNone(settings.SITE_NAME)
        self.assertEqual(settings.ARCHETYPES, "archetypes")
        self.assertEqual(settings.CONTENT, "content")
        self.assertEqual(settings.THEME, "default")
        self.assertEqual(settings.OUTPUT, "web")
        self.assertEqual(settings.TIMEZONE, "Europe/Rome")
        self.assertEqual(settings.SYSTEM_ASSETS, [])
        self.assertFalse(settings.DRAFT_MODE)
        self.assertTrue(settings.CACHE_REBUILDS)

    def test_default_name(self):
        output = os.path.join(self.build_root, "index.html")
        self.assertTrue(os.path.exists(output))

        with open(output, encoding="utf8") as fd:
            content = fd.read()

        # FIXME: this does not make sense anymore, since title is not defined
        # by settings anymore
        self.assertIn("Example web site", content)

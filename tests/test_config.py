from unittest import TestCase
from unittest import mock
from staticsite.cmd.command import SiteCommand
from staticsite.cmd.build import Build
from . import utils as test_utils
import os


class TestBuildSettings(TestCase):
    """
    Test settings after command line parsing
    """
    def test_defaults(self):
        with test_utils.workdir() as root:
            with mock.patch("os.getcwd", return_value=root):
                args = test_utils.Args()
                cmd = SiteCommand(args)
            settings = cmd.settings
            self.assertEqual(settings.PROJECT_ROOT, root)
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
        with test_utils.workdir(files) as root:
            with mock.patch("os.getcwd", return_value=root):
                args = test_utils.Args()
                cmd = SiteCommand(args)
            settings = cmd.settings
            self.assertEqual(settings.PROJECT_ROOT, root)
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
        with test_utils.workdir(files) as root:
            with mock.patch("os.getcwd", return_value=root):
                args = test_utils.Args()
                cmd = SiteCommand(args)
            settings = cmd.settings
            self.assertEqual(settings.PROJECT_ROOT, root)
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


class TestExampleProject(TestCase):
    def test_settings(self):
        with test_utils.example_site() as root:
            args = test_utils.Args(project=root)
            cmd = SiteCommand(args)
            settings = cmd.settings
            self.assertEqual(settings.PROJECT_ROOT, root)
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

    def _test_project(self, root, title='Example web site', cfg='', **kw):
        args = test_utils.Args(project=root + cfg, **kw)
        build = Build(args)
        build.settings.THEME_PATHS.append(os.path.join(os.getcwd(), "themes"))
        build.run()

        output = os.path.join(root, "web/index.html")
        self.assertTrue(os.path.exists(output))

        with open(output, "rt") as fd:
            content = fd.read()

        # FIXME: this does not make sense anymore, since title is not defined
        # by settings anymoer
        self.assertIn(title, content)

    def test_default_name(self):
        with test_utils.example_site() as root:
            self._test_project(root)

    def test_alt_name(self):
        with test_utils.example_site() as root:
            os.rename(os.path.join(root, 'settings.py'),
                      os.path.join(root, '.staticsite.py'))
            self._test_project(root)

    def test_custom_name(self):
        with test_utils.example_site() as root:
            os.rename(os.path.join(root, 'settings.py'),
                      os.path.join(root, 'otherconfig.py'))
            self._test_project(root, cfg='/otherconfig.py')

from unittest import TestCase
from staticsite.cmd.build import Build
from . import example_site, TestArgs
import os


class TestConfigfile(TestCase):
    def _test_project(self, root, title='Example web site', cfg=''):
        args = TestArgs(project=root + cfg)
        build = Build(args)
        build.run()

        output = os.path.join(root, "web/index.html")
        self.assertTrue(os.path.exists(output))

        with open(output, "rt") as fd:
            content = fd.read()

        self.assertIn(title, content)

    def test_default_name(self):
        with example_site() as root:
            self._test_project(root)

    def test_alt_name(self):
        with example_site() as root:
            os.rename(os.path.join(root, 'settings.py'),
                      os.path.join(root, '.staticsite.py'))
            self._test_project(root)

    def test_custom_name(self):
        with example_site() as root:
            os.rename(os.path.join(root, 'settings.py'),
                      os.path.join(root, 'otherconfig.py'))
            self._test_project(root, cfg='/otherconfig.py')

    def test_no_config(self):
        with example_site() as root:
            os.remove(os.path.join(root, 'settings.py'))
            self._test_project(root, title='Site name not set')

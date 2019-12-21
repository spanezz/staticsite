from unittest import TestCase
from staticsite.cmd.build import Build
from . import utils as test_utils
import os


class TestBuild(TestCase):
    # @test_utils.assert_no_logs()
    def test_dots(self):
        with test_utils.example_site() as root:
            args = test_utils.Args(project=root)
            build = Build(args)
            build.run()

            output = os.path.join(root, "web/.secret")
            self.assertFalse(os.path.exists(output))
            output = os.path.join(root, "web/.secrets")
            self.assertFalse(os.path.exists(output))

    def test_different_links(self):
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

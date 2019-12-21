from unittest import TestCase
from staticsite.cmd.build import Build
from . import utils as test_utils
import os


class TestMarkdownInJinja2(TestCase):
    def test_jinja2_markdown(self):
        with test_utils.example_site() as root:
            page = os.path.join(root, "content/test.j2.html")
            with open(page, "wt") as fd:
                fd.write("{% filter markdown %}*This* is an [example](http://example.org){% endfilter %}")

            args = test_utils.Args(project=root)
            build = Build(args)
            build.run()

            output = os.path.join(root, "web/test.html")
            self.assertTrue(os.path.exists(output))
            with open(output, "rt") as fd:
                content = fd.read()

            self.assertEqual(content, '<p><em>This</em> is an <a href="http://example.org">example</a></p>')


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

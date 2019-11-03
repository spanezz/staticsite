from unittest import TestCase
from staticsite.cmd.build import Build
from staticsite.site import Site
from . import datafile_abspath, example_site, TestArgs, TestPage
import os
import datetime


class TestSite(TestCase):
    def test_dirs(self):
        site = Site()

        page_root = TestPage(site, "page_root", date=datetime.datetime(2016, 1, 1))
        page_sub = TestPage(site, "dir1/page_sub", date=datetime.datetime(2016, 2, 1))
        page_sub3 = TestPage(site, "dir1/dir2/dir3/page_sub3", date=datetime.datetime(2016, 3, 1))

        site.add_page(page_root)
        site.add_page(page_sub)
        site.add_page(page_sub3)
        site.load_theme(datafile_abspath("theme"))
        site.analyze()

        # We have a root dir index and dir indices for all subdirs
        dir_root = site.pages[""]
        dir_dir1 = site.pages["dir1"]
        dir_dir2 = site.pages["dir1/dir2"]
        dir_dir3 = site.pages["dir1/dir2/dir3"]

        self.assertEqual(dir_root.TYPE, "dir")
        self.assertEqual(dir_dir1.TYPE, "dir")
        self.assertEqual(dir_dir3.TYPE, "dir")
        self.assertEqual(dir_dir3.TYPE, "dir")

        # Check the contents of all dirs
        self.assertEqual(dir_root.pages, [page_root])
        self.assertEqual(dir_root.subdirs, [dir_dir1])
        self.assertEqual(dir_dir1.pages, [page_sub])
        self.assertEqual(dir_dir1.subdirs, [dir_dir2])
        self.assertEqual(dir_dir2.pages, [])
        self.assertEqual(dir_dir2.subdirs, [dir_dir3])
        self.assertEqual(dir_dir3.pages, [page_sub3])
        self.assertEqual(dir_dir3.subdirs, [])


class TestMarkdownInJinja2(TestCase):
    def test_jinja2_markdown(self):
        with example_site() as root:
            page = os.path.join(root, "content/test.j2.html")
            with open(page, "wt") as fd:
                fd.write("{% filter markdown %}*This* is an [example](http://example.org){% endfilter %}")

            args = TestArgs(project=root)
            build = Build(args)
            build.run()

            output = os.path.join(root, "web/test.html")
            self.assertTrue(os.path.exists(output))
            with open(output, "rt") as fd:
                content = fd.read()

            self.assertEqual(content, '<p><em>This</em> is an <a href="http://example.org">example</a></p>')


class TestBuild(TestCase):
    def test_dots(self):
        with example_site() as root:
            args = TestArgs(project=root)
            build = Build(args)
            build.run()

            output = os.path.join(root, "web/.secret")
            self.assertFalse(os.path.exists(output))
            output = os.path.join(root, "web/.secrets")
            self.assertFalse(os.path.exists(output))

    def test_different_links(self):
        with example_site() as root:
            args = TestArgs(project=root)
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

# coding: utf-8
from unittest import TestCase
from staticsite.site import Site
from staticsite.core import Page
import datetime

class TestPage(Page):
    TYPE = "test"
    FINDABLE = True

    def __init__(self, site, relpath, dt):
        super().__init__(
            site=site,
            root_abspath="/",
            src_relpath=relpath,
            src_linkpath=relpath,
            dst_relpath=relpath,
            dst_link=relpath)
        self.dt = dt

    def read_metadata(self):
        self.meta["date"] = self.dt


class TestSite(TestCase):
    def test_dirs(self):
        site = Site()

        page_root = TestPage(site, "page_root", datetime.datetime(2016, 1, 1))
        page_sub = TestPage(site, "dir1/page_sub", datetime.datetime(2016, 2, 1))
        page_sub3 = TestPage(site, "dir1/dir2/dir3/page_sub3", datetime.datetime(2016, 3, 1))

        site.add_page(page_root)
        site.add_page(page_sub)
        site.add_page(page_sub3)
        site.load_theme("example/theme")
        site.analyze()

        # We have a root dir index and dir indices for all subdirs
        dir_root = site.pages[""]
        dir_dir1 = site.pages["dir1"]
        dir_dir2 = site.pages["dir1/dir2"]
        dir_dir3 = site.pages["dir1/dir2/dir3"]

        self.assertEquals(dir_root.TYPE, "dir")
        self.assertEquals(dir_dir1.TYPE, "dir")
        self.assertEquals(dir_dir3.TYPE, "dir")
        self.assertEquals(dir_dir3.TYPE, "dir")

        # Check the contents of all dirs
        self.assertEquals(dir_root.pages, [page_root])
        self.assertEquals(dir_root.subdirs, [dir_dir1])
        self.assertEquals(dir_dir1.pages, [page_sub])
        self.assertEquals(dir_dir1.subdirs, [dir_dir2])
        self.assertEquals(dir_dir2.pages, [])
        self.assertEquals(dir_dir2.subdirs, [dir_dir3])
        self.assertEquals(dir_dir3.pages, [page_dir3])
        self.assertEquals(dir_dir3.subdirs, [])

        #self.assertIn(site.pages[""].pages

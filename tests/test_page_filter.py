from unittest import TestCase
import re
from . import utils as test_utils
from staticsite.page_filter import PageFilter


def select(site, *args, **kw):
    f = PageFilter(site, *args, **kw)
    return [p.meta["site_path"] for p in f.filter(site.pages.values())]


class TestPageFilter(TestCase):
    def test_site(self):
        files = {
            # taxonomies are not findable pages
            "taxonomies/tags.taxonomy": {},
            "page.md": {},
            "blog/post1.md": {},
            "blog/post2.md": {},
        }
        with test_utils.testsite(files) as site:
            self.assertEqual(select(site, path="blog/*"), [
                "/blog/post1",
                "/blog/post2",
            ])

            self.assertEqual(select(site, path=r"^blog/"), [
                "/blog/post1",
                "/blog/post2",
            ])

            self.assertEqual(select(site, path=re.compile(r"^[tp]")), [
                "/page",
            ])

    def test_relative(self):
        files = {
            "page.md": {"pages": "dir/*"},
            "dir/page1.md": {"pages": "dir/*"},
            "dir/page2.md": {},
            "dir/dir/page3.md": {},
            "dir/dir/page4.md": {},
        }
        with test_utils.testsite(files) as site:
            page = site.pages["/page"]
            # dir1 = site.pages["dir"]
            dir2 = site.pages["/dir/dir"]
            page1 = site.pages["/dir/page1"]
            page2 = site.pages["/dir/page2"]
            page3 = site.pages["/dir/dir/page3"]
            page4 = site.pages["/dir/dir/page4"]

            self.assertCountEqual(page.meta["pages"], [page1, page2, page3, page4, dir2])
            self.assertCountEqual(page1.meta["pages"], [page3, page4])

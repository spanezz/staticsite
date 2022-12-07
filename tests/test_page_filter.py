from unittest import TestCase
import re
from . import utils as test_utils
from staticsite.page_filter import PageFilter


def select(mocksite, *args, **kw):
    f = PageFilter(mocksite.site, *args, **kw)
    return [p.site_path for p in f.filter()]


class TestPageFilter(test_utils.MockSiteTestMixin, TestCase):
    def test_site(self):
        files = {
            # taxonomies are not findable pages
            "taxonomies/tags.taxonomy": {},
            "page.md": {},
            "blog/post1.md": {},
            "blog/post2.md": {},
        }
        with self.site(files) as mocksite:
            mocksite.assertPagePaths(("", "page", "taxonomies/tags", "blog", "blog/post1", "blog/post2", "taxonomies"))

            self.assertCountEqual(select(mocksite, path="blog/*"), [
                "blog/post1",
                "blog/post2",
            ])

            self.assertCountEqual(select(mocksite, path=r"^blog/"), [
                "blog/post1",
                "blog/post2",
            ])

            self.assertEqual(select(mocksite, path=re.compile(r"^[tp]")), [
                "page",
            ])

    def test_relative(self):
        files = {
            "page.md": {"pages": "dir/*"},
            "dir/page1.md": {"pages": "dir/*"},
            "dir/page2.md": {},
            "dir/dir/page3.md": {},
            "dir/dir/page4.md": {},
        }
        with self.site(files) as mocksite:
            mocksite.assertPagePaths((
                "", "page", "dir", "dir/page1", "dir/page2", "dir/dir",
                "dir/dir/page3", "dir/dir/page4"))

            page, page1, page2, page3, page4 = mocksite.page(
                    "page", "dir/page1", "dir/page2", "dir/dir/page3", "dir/dir/page4")
            self.assertCountEqual(page.meta["pages"], [page1, page2, page3, page4])
            self.assertCountEqual(page1.meta["pages"], [page3, page4])

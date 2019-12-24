from unittest import TestCase
import re
from . import utils as test_utils
from staticsite.theme import PageFilter


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
        with test_utils.workdir(files) as root:
            site = test_utils.Site(TAXONOMIES=["tags"])
            site.load(content_root=root)
            site.analyze()

            self.assertEqual(select(site, path="blog/*"), [
                "blog/post1",
                "blog/post2",
            ])

            self.assertEqual(select(site, path=r"^blog/"), [
                "blog/post1",
                "blog/post2",
            ])

            self.assertEqual(select(site, path=re.compile(r"^[tp]")), [
                "page",
            ])

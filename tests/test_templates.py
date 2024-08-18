import os
from unittest import TestCase

from staticsite.theme import Theme

from . import utils as test_utils


class MockPage:
    def __init__(self, **kw):
        self.meta = kw
        for k, v in kw.items():
            setattr(self, k, v)

    def __str__(self):
        return str(self.site_path)

    def __repr__(self):
        return str(self.site_path)


class TestTemplates(test_utils.MockSiteTestMixin, TestCase):
    def test_arrange(self):
        with self.site({}) as mocksite:
            theme = Theme(mocksite.site, "test", [{"root": ".", "name": "test"}])
            theme.load()

            self.maxDiff = None

            # Small list
            pages = [MockPage(site_path=x, date=-x) for x in range(10)]

            expr = theme.jinja2.compile_expression("pages|arrange('url')")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.site_path)
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-url')")
            self.assertEqual(
                expr(pages=pages),
                sorted(pages, key=lambda x: x.site_path, reverse=True),
            )

            expr = theme.jinja2.compile_expression("pages|arrange('url', 5)")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.site_path)[:5]
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-url', 5)")
            self.assertEqual(
                expr(pages=pages),
                sorted(pages, key=lambda x: x.site_path, reverse=True)[:5],
            )

            expr = theme.jinja2.compile_expression("pages|arrange('url', 15)")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.site_path)
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-url', 15)")
            self.assertEqual(
                expr(pages=pages),
                sorted(pages, key=lambda x: x.site_path, reverse=True),
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-date')")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.date, reverse=True)
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-date', 5)")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.date, reverse=True)[:5]
            )

            expr = theme.jinja2.compile_expression("pages|arrange('date', 5)")
            self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.date)[:5])

            # Limit = 1

            expr = theme.jinja2.compile_expression("pages|arrange('url', 1)")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.site_path)[:1]
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-url', 1)")
            self.assertEqual(
                expr(pages=pages),
                sorted(pages, key=lambda x: x.site_path, reverse=True)[:1],
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-date', 1)")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.date, reverse=True)[:1]
            )

            expr = theme.jinja2.compile_expression("pages|arrange('date', 1)")
            self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.date)[:1])

            # Large list

            pages = [MockPage(site_path=x, date=-x) for x in range(100)]

            expr = theme.jinja2.compile_expression("pages|arrange('url', 5)")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.site_path)[:5]
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-url', 5)")
            self.assertEqual(
                expr(pages=pages),
                sorted(pages, key=lambda x: x.site_path, reverse=True)[:5],
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-date', 5)")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.date, reverse=True)[:5]
            )

            expr = theme.jinja2.compile_expression("pages|arrange('date', 5)")
            self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.date)[:5])

            expr = theme.jinja2.compile_expression("pages|arrange('url', 50)")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.site_path)[:50]
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-url', 50)")
            self.assertEqual(
                expr(pages=pages),
                sorted(pages, key=lambda x: x.site_path, reverse=True)[:50],
            )

            expr = theme.jinja2.compile_expression("pages|arrange('-date', 50)")
            self.assertEqual(
                expr(pages=pages),
                sorted(pages, key=lambda x: x.date, reverse=True)[:50],
            )

            expr = theme.jinja2.compile_expression("pages|arrange('date', 50)")
            self.assertEqual(
                expr(pages=pages), sorted(pages, key=lambda x: x.date)[:50]
            )

    def test_page_template_conflicts(self):
        self.maxDiff = None

        files = {
            "index.md": {},
            "page.html": "",
        }

        with self.site(files) as mocksite:
            site = mocksite.site
            mocksite.assertPagePaths(("", "page.html"))
            index, page = mocksite.page("", "page.html")

            self.assertEqual(
                index.to_dict(),
                {
                    "src": {
                        "relpath": "index.md",
                        "abspath": os.path.join(site.content_root, "index.md"),
                    },
                    "site_path": "",
                    "build_path": "index.html",
                    "meta": {
                        "author": "Test User",
                        "copyright": "© 2019 Test User",
                        "date": "2019-06-01 12:30:00+02:00",
                        "draft": False,
                        "indexed": True,
                        "syndicated": True,
                        "syndication_date": "2019-06-01 12:30:00+02:00",
                        "site_name": "Test site",
                        "site_url": "https://www.example.org",
                        "template": "page.html",
                        "template_copyright": "compiled:None",
                        "title": "Test site",
                        "related": {},
                        "nav": [],
                    },
                    "type": "markdown",
                },
            )

            rendered = index.render().content()
            self.assertIn(b"Test site", rendered)

            self.assertEqual(
                page.to_dict(),
                {
                    "src": {
                        "relpath": "page.html",
                        "abspath": os.path.join(site.content_root, "page.html"),
                    },
                    "site_path": "page.html",
                    "build_path": "page.html",
                    "meta": {
                        "author": "Test User",
                        "copyright": "© 2019 Test User",
                        "date": "2019-06-01 12:30:00+02:00",
                        "draft": False,
                        "indexed": True,
                        "syndicated": True,
                        "syndication_date": "2019-06-01 12:30:00+02:00",
                        "site_name": "Test site",
                        "site_url": "https://www.example.org",
                        "template": "compiled:page.html",
                        "template_copyright": "compiled:None",
                        "title": "Test site",
                        "related": {},
                        "nav": [],
                    },
                    "type": "jinja2",
                },
            )

            rendered = page.render().content()
            self.assertEqual(b"", rendered)

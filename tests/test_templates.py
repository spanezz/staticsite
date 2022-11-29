from unittest import TestCase
from . import utils as test_utils
from staticsite.theme import Theme
import os


class MockPage:
    def __init__(self, *, site_path, **kw):
        self.meta = kw
        self.site_path = site_path

    def __str__(self):
        return str(self.meta["site_path"])

    def __repr__(self):
        return str(self.meta["site_path"])


class TestTemplates(TestCase):
    def test_arrange(self):
        site = test_utils.Site()
        theme = Theme(site, "test", [{"root": ".", "name": "test"}])
        theme.load()

        self.maxDiff = None

        # Small list
        pages = [MockPage(site_path=x, date=-x) for x in range(10)]

        expr = theme.jinja2.compile_expression("pages|arrange('url')")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path))

        expr = theme.jinja2.compile_expression("pages|arrange('-url')")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path, reverse=True))

        expr = theme.jinja2.compile_expression("pages|arrange('url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path, reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('url', 15)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path))

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 15)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path, reverse=True))

        expr = theme.jinja2.compile_expression("pages|arrange('-date')")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True))

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:5])

        # Limit = 1

        expr = theme.jinja2.compile_expression("pages|arrange('url', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path)[:1])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path, reverse=True)[:1])

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:1])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:1])

        # Large list

        pages = [MockPage(site_path=x, date=-x) for x in range(100)]

        expr = theme.jinja2.compile_expression("pages|arrange('url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path, reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('url', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path)[:50])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_path, reverse=True)[:50])

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:50])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:50])

    def test_page_template_conflicts(self):
        self.maxDiff = None

        files = {
            "index.md": {},
            "page.html": "",
        }

        with test_utils.testsite(files) as site:
            self.assertCountEqual([k for k in site.pages.keys() if not k.startswith("static/")], [
                "", "page.html"
            ])

            index = site.pages[""]
            page = site.pages["page.html"]

            self.assertEqual(index.to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                'site_path': '',
                "build_path": "index.html",
                "meta": {
                    "author": "Test User",
                    "copyright": '© 2019 Test User',
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'indexed': True,
                    'syndicated': True,
                    "syndication_date": '2019-06-01 12:30:00+02:00',
                    'site_name': 'Test site',
                    'site_url': 'https://www.example.org',
                    'template': 'page.html',
                    'title': 'Test site',
                    'related': {},
                },
                "type": "markdown",
            })

            rendered = index.render().content()
            self.assertIn(b"Test site", rendered)

            self.assertEqual(page.to_dict(), {
                "src": {
                    "relpath": "page.html",
                    "abspath": os.path.join(site.content_root, "page.html"),
                },
                'site_path': 'page.html',
                "build_path": "page.html",
                "meta": {
                    "author": "Test User",
                    "copyright": '© 2019 Test User',
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'indexed': True,
                    'syndicated': True,
                    "syndication_date": '2019-06-01 12:30:00+02:00',
                    'site_name': 'Test site',
                    'site_url': 'https://www.example.org',
                    'template': 'compiled:page.html',
                    'title': 'Test site',
                    'related': {},
                },
                "type": "jinja2",
            })

            rendered = page.render().content()
            self.assertEqual(b"", rendered)

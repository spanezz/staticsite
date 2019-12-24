from unittest import TestCase
from . import utils as test_utils
from staticsite.theme import Theme


class MockPage:
    def __init__(self, **kw):
        self.meta = kw

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
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"]))

        expr = theme.jinja2.compile_expression("pages|arrange('-url')")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"], reverse=True))

        expr = theme.jinja2.compile_expression("pages|arrange('url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"])[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"], reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('url', 15)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"]))

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 15)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"], reverse=True))

        expr = theme.jinja2.compile_expression("pages|arrange('-date')")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True))

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:5])

        # Limit = 1

        expr = theme.jinja2.compile_expression("pages|arrange('url', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"])[:1])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"], reverse=True)[:1])

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:1])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:1])

        # Large list

        pages = [MockPage(site_path=x, date=-x) for x in range(100)]

        expr = theme.jinja2.compile_expression("pages|arrange('url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"])[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"], reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('url', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"])[:50])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["site_path"], reverse=True)[:50])

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:50])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:50])

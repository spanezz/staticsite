from unittest import TestCase
from . import utils as test_utils
from staticsite.theme import Theme


class MockPage:
    def __init__(self, site_relpath, **kw):
        self.site_relpath = site_relpath
        self.meta = kw

    def __str__(self):
        return str(self.site_relpath)

    def __repr__(self):
        return str(self.site_relpath)


class TestTemplates(TestCase):
    def test_arrange(self):
        site = test_utils.Site()
        theme = Theme(site, ".")

        self.maxDiff = None

        # Small list
        pages = [MockPage(site_relpath=x, date=-x) for x in range(10)]

        expr = theme.jinja2.compile_expression("pages|arrange('url')")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath))

        expr = theme.jinja2.compile_expression("pages|arrange('-url')")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath, reverse=True))

        expr = theme.jinja2.compile_expression("pages|arrange('url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath, reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('url', 15)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath))

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 15)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath, reverse=True))

        expr = theme.jinja2.compile_expression("pages|arrange('-date')")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True))

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:5])

        # Limit = 1

        expr = theme.jinja2.compile_expression("pages|arrange('url', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath)[:1])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath, reverse=True)[:1])

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:1])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 1)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:1])

        # Large list

        pages = [MockPage(site_relpath=x, date=-x) for x in range(100)]

        expr = theme.jinja2.compile_expression("pages|arrange('url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath, reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 5)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:5])

        expr = theme.jinja2.compile_expression("pages|arrange('url', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath)[:50])

        expr = theme.jinja2.compile_expression("pages|arrange('-url', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.site_relpath, reverse=True)[:50])

        expr = theme.jinja2.compile_expression("pages|arrange('-date', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"], reverse=True)[:50])

        expr = theme.jinja2.compile_expression("pages|arrange('date', 50)")
        self.assertEqual(expr(pages=pages), sorted(pages, key=lambda x: x.meta["date"])[:50])

from unittest import TestCase

from . import utils as test_utils


class MockContext(dict):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.name = "test"


class TestUrlFor(test_utils.MockSiteTestMixin, TestCase):
    """
    Test theme functions
    """

    def test_no_site_root(self):
        files = {
            ".staticsite": {
                "site_url": "https://www.example.org",
            },
            "page1.md": {},
            "dir/page2.md": {},
            "dir/index.html": {},
        }

        with self.site(files) as mocksite:
            site = mocksite.site

            def url_for(dest, page=None, **kw):
                if page:
                    context = MockContext(page=page)
                else:
                    context = None
                return site.theme.jinja2_url_for(context, dest, **kw)

            page = mocksite.page("")
            self.assertEqual(url_for("page1.md", page=page), "/page1")
            self.assertEqual(url_for("page1", page=page), "/page1")

            # Autogenerated index.html can be looked up now
            self.assertEqual(url_for("page1/index.html", page=page), "/page1")

            # index.html however resolve, as they exist in the sources
            # namespace
            self.assertEqual(url_for("dir", page=page), "/dir")
            self.assertEqual(url_for("dir/index.html", page=page), "/dir")

            # Test absolute urls
            self.assertEqual(
                url_for("page1", page=page, absolute=True),
                "https://www.example.org/page1",
            )

    def test_site_path(self):
        files = {
            ".staticsite": {
                "site_url": "https://www.example.org",
                "site_path": "prefix",
            },
            "page1.md": {},
            "page2.rst": {},
            "page3.yaml": {"data_type": "page"},
            "dir/page2.md": {},
            "dir/index.html": {},
        }

        with self.site(files) as mocksite:
            site = mocksite.site

            def url_for(dest, page=None, **kw):
                if page:
                    context = MockContext(page=page)
                else:
                    context = None
                return site.theme.jinja2_url_for(context, dest, **kw)

            page = mocksite.page("")
            self.assertEqual(url_for("page1.md", page=page), "/prefix/page1")
            self.assertEqual(url_for("page1", page=page), "/prefix/page1")

            self.assertEqual(url_for("page2.rst", page=page), "/prefix/page2")
            self.assertEqual(url_for("page2", page=page), "/prefix/page2")

            self.assertEqual(url_for("page3.yaml", page=page), "/prefix/page3")
            self.assertEqual(url_for("page3", page=page), "/prefix/page3")

            # Test absolute urls
            self.assertEqual(
                url_for("page1", page=page, absolute=True),
                "https://www.example.org/prefix/page1",
            )


class TestMarkdownFilter(test_utils.MockSiteTestMixin, TestCase):
    def test_markdown(self):
        files = {
            "index.html": "",
        }
        with self.site(files) as mocksite:
            site = mocksite.site

            page = mocksite.page("")

            tpl = site.theme.jinja2.from_string(
                "{% filter markdown %}*This* is an [example](http://example.org){% endfilter %}"
            )

            res = tpl.render(page=page)
            self.assertEqual(
                res,
                '<p><em>This</em> is an <a href="http://example.org">example</a></p>',
            )

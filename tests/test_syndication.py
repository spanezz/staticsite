from __future__ import annotations

from unittest import TestCase

from . import utils as test_utils

BASE_FILES = {
    "blog/post1.rst": """
:date: 2016-04-16 10:23:00+02:00

Example blog post in reStructuredText
=====================================
""",
    "blog/post2.md": """---
date: 2016-04-17 10:00
---
# Post 2
""",
    "blog/widget.md": {"syndicated": False},
}


class TestSyndication(test_utils.MockSiteTestMixin, TestCase):
    def test_simple(self):
        files = dict(BASE_FILES)
        files["blog.md"] = """---
date: 2016-04-16 10:23:00+02:00
pages: blog/*
syndication: yes
---

# Title

text
"""
        with self.site(files) as mocksite:
            blog, post1, post2, widget, rss, atom = mocksite.page(
                    "blog", "blog/post1", "blog/post2", "blog/widget", "blog/index.rss", "blog/index.atom")

            synd = blog.syndication
            self.assertEqual(synd.pages, [post2, post1])

            self.assertIsNone(post1.syndication)
            self.assertEqual(post1.related, {
                "rss_feed": rss,
                "atom_feed": atom,
            })

            self.assertIsNone(post2.syndication)
            self.assertEqual(post2.related, {
                "rss_feed": rss,
                "atom_feed": atom,
            })

            self.assertEqual(rss.pages, synd.pages)
            self.assertEqual(rss.title, blog.title)

            self.assertEqual(atom.pages, synd.pages)
            self.assertEqual(atom.title, blog.title)

            self.assertIsNone(widget.syndication)

    def test_add_to_false(self):
        files = dict(BASE_FILES)
        files["blog.md"] = """---
date: 2016-04-16 10:23:00+02:00
pages: blog/*
syndication:
  title: Syndication
  add_to: no
---

# Title

text
"""
        with self.site(files) as mocksite:
            blog, post1, post2, widget, rss, atom = mocksite.page(
                    "blog", "blog/post1", "blog/post2", "blog/widget", "blog/index.rss", "blog/index.atom")

            synd = blog.syndication
            self.assertEqual(synd.pages, [post2, post1])

            self.assertIsNone(post1.syndication)
            self.assertIsNone(post2.syndication)
            self.assertIsNone(widget.syndication)

            self.assertEqual(rss.pages, synd.pages)
            self.assertEqual(rss.title, "Syndication")

            self.assertEqual(atom.pages, synd.pages)
            self.assertEqual(atom.title, "Syndication")

    def test_complex(self):
        files = dict(BASE_FILES)
        files["blog.md"] = """---
date: 2016-04-16 10:23:00+02:00
pages: blog/*2.*
syndication:
  add_to:
    path: blog/*1.*
---

# Title

text
"""
        with self.site(files) as mocksite:
            blog, post1, post2, widget, rss, atom = mocksite.page(
                    "blog", "blog/post1", "blog/post2", "blog/widget", "blog/index.rss", "blog/index.atom")

            synd = blog.syndication
            self.assertEqual(synd.pages, [post2])

            self.assertIsNone(post1.syndication)
            self.assertEqual(post1.related, {
                "rss_feed": rss,
                "atom_feed": atom,
            })
            self.assertIsNone(post2.syndication)
            self.assertIsNone(widget.syndication)
            self.assertEqual(rss.pages, synd.pages)
            self.assertEqual(atom.pages, synd.pages)

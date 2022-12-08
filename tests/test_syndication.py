from __future__ import annotations
from unittest import TestCase
import re
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

            synd = blog.meta["syndication"]
            self.assertEqual(synd.pages, [post2, post1])

            self.assertNotIn("syndication", post1.meta)
            self.assertEqual(post1.meta["related"], {
                "rss_feed": rss,
                "atom_feed": atom,
            })
            self.assertNotIn("syndication", post2.meta)
            self.assertEqual(post2.meta["related"], {
                "rss_feed": rss,
                "atom_feed": atom,
            })
            self.assertEqual(rss.meta["pages"], synd.pages)
            self.assertEqual(atom.meta["pages"], synd.pages)
            self.assertNotIn("syndication", widget.meta)

    def test_add_to_false(self):
        files = dict(BASE_FILES)
        files["blog.md"] = """---
date: 2016-04-16 10:23:00+02:00
pages: blog/*
syndication:
  add_to: no
---

# Title

text
"""
        with self.site(files) as mocksite:
            blog, post1, post2, widget, rss, atom = mocksite.page(
                    "blog", "blog/post1", "blog/post2", "blog/widget", "blog/index.rss", "blog/index.atom")

            synd = blog.meta["syndication"]
            self.assertEqual(synd.pages, [post2, post1])

            self.assertNotIn("syndication", post1.meta)
            self.assertNotIn("syndication", post2.meta)
            self.assertNotIn("syndication", widget.meta)
            self.assertEqual(rss.meta["pages"], synd.pages)
            self.assertEqual(atom.meta["pages"], synd.pages)

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

            synd = blog.meta["syndication"]
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

    def test_images(self):
        self.maxDiff = None
        files = {
            "index.md": """---
date: 2019-01-01 12:00:00+02:00
syndication: yes
pages: "blog/*"
template: blog.html
---

# Blog
""",
            "blog/post.md": """---
date: 2019-01-01 12:00:00+02:00
---

# Title

![Photo](images/photo.xpm)
""",
            "blog/images/photo.xpm": """/* XPM */
static char * bottom_active_xpm[] = {
"24 3 3 1",
"       c None",
"#      c #C0C0C0 s active_color_2",
"@      c #C0C0FF s active_color_2",
"@@@@@@@@@@@@@@@@@@@@@@@@",
"@@@@@@@@@@@@@@@@@@@@@@@@",
"@@@@@@@@@@@@@@@@@@@@@@@@"};
""",
        }
        with self.site(files) as mocksite:
            mocksite.assertPagePaths((
                "",
                "index.rss",
                "index.atom",
                "archive",
                "blog",
                "blog/post",
                "blog/images",
                "blog/images/photo.xpm",
            ))

            post = mocksite.page("")
            rendered = post.render().buf
            mo = re.search(r'src="([a-z/:.]+)/photo.xpm"', rendered.decode())
            self.assertTrue(mo)
            self.assertEqual(mo.group(1), "https://www.example.org/blog/images")

            post = mocksite.page("blog/post")
            rendered = post.render().buf
            mo = re.search(r'src="([a-z/:.]+)/photo.xpm"', rendered.decode())
            self.assertTrue(mo)
            self.assertEqual(mo.group(1), "/blog/images")

            rss = mocksite.page("index.rss")
            rendered = rss.render().buf
            mo = re.search(r'src=&#34;([a-z/:.]+)/photo.xpm&#34;', rendered.decode())
            self.assertEqual(mo.group(1), "https://www.example.org/blog/images")

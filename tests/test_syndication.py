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


class TestSyndication(TestCase):
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

        with test_utils.testsite(files) as site:
            blog = site.pages["/blog"]
            post1 = site.pages["/blog/post1"]
            post2 = site.pages["/blog/post2"]
            widget = site.pages["/blog/widget"]
            rss = site.pages["/blog/index.rss"]
            atom = site.pages["/blog/index.atom"]

            synd = blog.meta["syndication"]
            self.assertEqual(synd["pages"], [post2, post1])

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
            self.assertEqual(rss.meta["pages"], synd["pages"])
            self.assertEqual(atom.meta["pages"], synd["pages"])
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
        with test_utils.testsite(files) as site:
            blog = site.pages["/blog"]
            post1 = site.pages["/blog/post1"]
            post2 = site.pages["/blog/post2"]
            widget = site.pages["/blog/widget"]
            rss = site.pages["/blog/index.rss"]
            atom = site.pages["/blog/index.atom"]

            synd = blog.meta["syndication"]
            self.assertEqual(synd["pages"], [post2, post1])

            self.assertNotIn("syndication", post1.meta)
            self.assertNotIn("syndication", post2.meta)
            self.assertNotIn("syndication", widget.meta)
            self.assertEqual(rss.meta["pages"], synd["pages"])
            self.assertEqual(atom.meta["pages"], synd["pages"])

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

        with test_utils.testsite(files) as site:
            blog = site.pages["/blog"]
            post1 = site.pages["/blog/post1"]
            post2 = site.pages["/blog/post2"]
            widget = site.pages["/blog/widget"]
            rss = site.pages["/blog/index.rss"]
            atom = site.pages["/blog/index.atom"]

            synd = blog.meta["syndication"]
            self.assertEqual(synd["pages"], [post2])

            self.assertNotIn("syndication", post1.meta)
            self.assertEqual(post1.meta["related"], {
                "rss_feed": rss,
                "atom_feed": atom,
            })
            self.assertNotIn("syndication", post2.meta)
            self.assertNotIn("syndication", widget.meta)
            self.assertEqual(rss.meta["pages"], synd["pages"])
            self.assertEqual(atom.meta["pages"], synd["pages"])

from __future__ import annotations

import re
from unittest import TestCase

from . import utils as test_utils

SVG = """
<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN"
  "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
<svg width="24" height="24">
  <text x="0" y="5">2</text>
</svg>
"""

XPM = """/* XPM */
static char * bottom_active_xpm[] = {
"24 3 3 1",
"       c None",
"#      c #C0C0C0 s active_color_2",
"@      c #C0C0FF s active_color_2",
"@@@@@@@@@@@@@@@@@@@@@@@@",
"@@@@@@@@@@@@@@@@@@@@@@@@",
"@@@@@@@@@@@@@@@@@@@@@@@@"};
"""


class TestImages(test_utils.MockSiteTestMixin, TestCase):
    def test_images(self):
        self.maxDiff = None
        files = {
            "index.md": {
                "syndication": True,
                "pages": "blog/*",
                "template": "blog.html",
                "title": "Blog",
            },
            "blog/post.md": """---
date: 2019-01-01 12:00:00+02:00
---

# Title

![Photo](images/photo.xpm)

![Photo](images/photo.svg)
""",
            "blog/images/photo.xpm": XPM,
            "blog/images/photo.svg": SVG,
        }
        with self.site(files) as mocksite:
            mocksite.assertPagePaths(
                (
                    "",
                    "index.rss",
                    "index.atom",
                    "archive",
                    "blog",
                    "blog/post",
                    "blog/images",
                    "blog/images/photo.xpm",
                    "blog/images/photo.svg",
                )
            )

            post = mocksite.page("")
            rendered = post.render().buf
            mo = re.search(r'src="([a-z/:.]+)/photo.xpm"', rendered.decode())
            self.assertTrue(mo)
            self.assertEqual(mo.group(1), "https://www.example.org/blog/images")
            mo = re.search(r'src="([a-z/:.]+)/photo.svg"', rendered.decode())
            self.assertTrue(mo)
            self.assertEqual(mo.group(1), "https://www.example.org/blog/images")

            post = mocksite.page("blog/post")
            rendered = post.render().buf
            mo = re.search(r'src="([a-z/:.]+)/photo.xpm"', rendered.decode())
            self.assertTrue(mo)
            self.assertEqual(mo.group(1), "/blog/images")
            mo = re.search(r'src="([a-z/:.]+)/photo.svg"', rendered.decode())
            self.assertTrue(mo)
            self.assertEqual(mo.group(1), "/blog/images")

            rss = mocksite.page("index.rss")
            rendered = rss.render().buf
            mo = re.search(r"src=&#34;([a-z/:.]+)/photo.xpm&#34;", rendered.decode())
            self.assertEqual(mo.group(1), "https://www.example.org/blog/images")
            mo = re.search(r"src=&#34;([a-z/:.]+)/photo.svg&#34;", rendered.decode())
            self.assertEqual(mo.group(1), "https://www.example.org/blog/images")

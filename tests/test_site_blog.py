from unittest import TestCase
from . import utils as test_utils
import os


class TestSite(TestCase):
    def test_meta(self):
        self.maxDiff = None

        with test_utils.example_site("blog", SITE_AUTHOR="Test User") as site:
            site_paths = [path for path in site.pages.keys() if not path.startswith("/static/")]
            self.assertCountEqual(site_paths, [
                "/", "/index.rss", "/index.atom", "/archive",
                "/about",
                "/posts", "/posts/example",
                "/posts/example.jpg", "/posts/example-small.jpg", "/posts/example-thumbnail.jpg",
            ])

            page = site.pages["/about"]
            self.assertEqual(page.meta["title"], "About")

            self.assertEqual(site.pages["/about"].to_dict(), {
                "src": {
                    "relpath": "about.md",
                    "abspath": os.path.join(site.content_root, "about.md"),
                },
                "meta": {
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': True,
                    'syndicated': True,
                    "syndication_date": '2019-06-01 12:30:00+02:00',
                    'site_name': 'My example blog',
                    'site_path': '/about',
                    'site_url': 'https://www.example.org',
                    "build_path": "about/index.html",
                    'template': 'page.html',
                    'title': 'About',
                    'nav': ['MarkdownPage(/about)'],
                    'nav_title': 'About',
                    'related': {},
                },
                "type": "markdown",
            })

            self.assertEqual(site.pages["/"].to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                "meta": {
                    "date": '2019-12-30 17:30:00+01:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': True,
                    'syndicated': True,
                    'syndication': {'atom_page': 'AtomPage(/index.atom)',
                                    'index': 'MarkdownPage(/)',
                                    'pages': ['MarkdownPage(/posts/example)'],
                                    'rss_page': 'RSSPage(/index.rss)'},
                    'syndication_date': '2019-06-01 12:30:00+02:00',
                    'pages': ['MarkdownPage(/posts/example)'],
                    'site_name': 'My example blog',
                    'site_path': '/',
                    'site_url': 'https://www.example.org',
                    "build_path": "index.html",
                    'template': 'blog.html',
                    'title': 'My example blog',
                    'nav': ['MarkdownPage(/about)'],
                    'related': {
                        'archive': 'ArchivePage(/archive)',
                        'atom_feed': 'AtomPage(/index.atom)',
                        'rss_feed': 'RSSPage(/index.rss)',
                    },
                },
                "type": "markdown",
            })
            # A blog page renders images, relative links, only the beginning of
            # split pages
            rendered = site.pages["/"].render()
            self.assertCountEqual(rendered.keys(), ["index.html"])
            rendered = rendered["index.html"].content()
            self.assertNotIn(b"This is the rest of the blog post", rendered)
            self.assertIn(b"srcset='/posts/example", rendered)

            self.assertEqual(site.pages["/archive"].to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                "meta": {
                    "date": '2019-12-30 17:30:00+01:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'pages': ['MarkdownPage(/posts/example)'],
                    'site_name': 'My example blog',
                    'site_path': '/archive',
                    'site_url': 'https://www.example.org',
                    "build_path": "archive/index.html",
                    'template': 'archive.html',
                    'title': 'My example blog',
                    'nav': ['MarkdownPage(/about)'],
                    'related': {
                        'atom_feed': 'AtomPage(/index.atom)',
                        'rss_feed': 'RSSPage(/index.rss)',
                    },
                },
                "type": "archive",
            })

            self.assertEqual(site.pages["/index.rss"].to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                "meta": {
                    "date": '2019-12-30 17:30:00+01:00',
                    "draft": False,
                    'index': 'MarkdownPage(/)',
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'pages': ['MarkdownPage(/posts/example)'],
                    'site_name': 'My example blog',
                    'site_path': '/index.rss',
                    'site_url': 'https://www.example.org',
                    "build_path": "index.rss",
                    'template': 'syndication.rss',
                    'title': 'My example blog',
                    'nav': ['MarkdownPage(/about)'],
                    'related': {},
                },
                "type": "rss",
            })
            # A feed page renders images, all of a split page, absolute site urls
            rendered = site.pages["/index.rss"].render()
            self.assertCountEqual(rendered.keys(), ["index.rss"])
            rendered = rendered["index.rss"].content()
            self.assertIn(b"src='https://www.example.org/posts/example-small.jpg", rendered)
            self.assertIn(b"This is the rest of the blog post", rendered)

            self.assertEqual(site.pages["/posts/example.jpg"].to_dict(), {
                "src": {
                    "relpath": "posts/example.jpg",
                    "abspath": os.path.join(site.content_root, "posts/example.jpg"),
                },
                "meta": {
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'site_name': 'My example blog',
                    'site_path': '/posts/example.jpg',
                    'site_url': 'https://www.example.org',
                    "build_path": "posts/example.jpg",
                    'template': 'page.html',
                    'title': 'This is an example image',
                    'width': 500,
                    'height': 477,
                    'nav': ['MarkdownPage(/about)'],
                    'related': {
                        'small': 'ScaledImage(/posts/example-small.jpg)',
                        'thumbnail': 'ScaledImage(/posts/example-thumbnail.jpg)',
                    },
                },
                "type": "image",
            })

            self.assertEqual(site.pages["/posts/example-small.jpg"].to_dict(), {
                "src": {
                    "relpath": "posts/example.jpg",
                    "abspath": os.path.join(site.content_root, "posts/example.jpg"),
                },
                "meta": {
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'site_name': 'My example blog',
                    'site_path': '/posts/example-small.jpg',
                    'site_url': 'https://www.example.org',
                    "build_path": "posts/example-small.jpg",
                    'template': 'page.html',
                    'title': 'This is an example image',
                    'width': 480,
                    'height': 458,
                    'nav': ['MarkdownPage(/about)'],
                    'related': {},
                },
                "type": "image",
            })

            self.assertEqual(site.pages["/posts/example-thumbnail.jpg"].to_dict(), {
                "src": {
                    "relpath": "posts/example.jpg",
                    "abspath": os.path.join(site.content_root, "posts/example.jpg"),
                },
                "meta": {
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'site_name': 'My example blog',
                    'site_path': '/posts/example-thumbnail.jpg',
                    'site_url': 'https://www.example.org',
                    "build_path": "posts/example-thumbnail.jpg",
                    'template': 'page.html',
                    'title': 'This is an example image',
                    'width': 128,
                    'height': 122,
                    'nav': ['MarkdownPage(/about)'],
                    'related': {},
                },
                "type": "image",
            })

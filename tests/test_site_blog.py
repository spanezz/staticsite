from unittest import TestCase
from . import utils as test_utils
import os


class TestSite(TestCase):
    def test_meta(self):
        self.maxDiff = None

        with test_utils.example_site("blog", SITE_AUTHOR="Test User") as site:
            site_paths = [path for path in site.pages.keys() if not path.startswith("static/")]
            self.assertCountEqual(site_paths, [
                "", "index.rss", "index.atom", "archive",
                "about",
                "posts", "posts/example",
                "posts/example.jpg", "posts/example-small.jpg", "posts/example-thumbnail.jpg",
            ])

            page = site.pages["about"]
            self.assertEqual(page.meta["title"], "About")

            self.assertEqual(site.pages["about"].to_dict(), {
                "src": {
                    "relpath": "about.md",
                    "abspath": os.path.join(site.content_root, "about.md"),
                },
                'site_path': 'about',
                "build_path": "about/index.html",
                "meta": {
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': True,
                    'syndicated': True,
                    "syndication_date": '2019-06-01 12:30:00+02:00',
                    'site_name': 'My example blog',
                    'site_url': 'https://www.example.org',
                    'template': 'page.html',
                    'title': 'About',
                    'nav': ['MarkdownPage(about)'],
                    'nav_title': 'About',
                    'related': {},
                },
                "type": "markdown",
            })

            self.assertEqual(site.pages[""].to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                'site_path': '',
                "build_path": "index.html",
                "meta": {
                    "date": '2019-12-30 17:30:00+01:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'template_copyright': 'compiled:None',
                    'indexed': True,
                    'syndicated': True,
                    'syndication': {'atom_page': 'AtomPage(index.atom)',
                                    'index': 'MarkdownPage()',
                                    'pages': ['MarkdownPage(posts/example)'],
                                    'rss_page': 'RSSPage(index.rss)'},
                    'syndication_date': '2019-06-01 12:30:00+02:00',
                    'pages': ['MarkdownPage(posts/example)'],
                    'site_name': 'My example blog',
                    'site_url': 'https://www.example.org',
                    'site_path': '/',
                    'template': 'blog.html',
                    'title': 'My example blog',
                    'nav': ['MarkdownPage(about)'],
                    'related': {
                        'archive': 'ArchivePage(archive)',
                        'atom_feed': 'AtomPage(index.atom)',
                        'rss_feed': 'RSSPage(index.rss)',
                    },
                },
                "type": "markdown",
            })
            # A blog page renders images, relative links, only the beginning of
            # split pages
            rendered = site.pages[""].render().content()
            self.assertNotIn(b"This is the rest of the blog post", rendered)
            self.assertIn(b"srcset='/posts/example", rendered)

            self.assertEqual(site.pages["archive"].to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                'site_path': 'archive',
                "build_path": "archive/index.html",
                "meta": {
                    "date": '2019-12-30 17:30:00+01:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'created_from': 'MarkdownPage()',
                    'index': 'MarkdownPage()',
                    'indexed': False,
                    'syndicated': False,
                    'pages': ['MarkdownPage(posts/example)'],
                    'site_name': 'My example blog',
                    'site_url': 'https://www.example.org',
                    'template': 'archive.html',
                    'title': 'My example blog',
                    'nav': ['MarkdownPage(about)'],
                    'related': {
                        'atom_feed': 'AtomPage(index.atom)',
                        'rss_feed': 'RSSPage(index.rss)',
                    },
                },
                "type": "archive",
            })

            self.assertEqual(site.pages["index.rss"].to_dict(), {
                "src": {
                    "relpath": "index.md",
                    "abspath": os.path.join(site.content_root, "index.md"),
                },
                'site_path': 'index.rss',
                "build_path": "index.rss",
                "meta": {
                    'created_from': 'MarkdownPage()',
                    "date": '2019-12-30 17:30:00+01:00',
                    "draft": False,
                    'index': 'MarkdownPage()',
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'pages': ['MarkdownPage(posts/example)'],
                    'rss_page': 'RSSPage(index.rss)',
                    'site_name': 'My example blog',
                    'site_url': 'https://www.example.org',
                    'template': 'syndication.rss',
                    'title': 'My example blog',
                    'nav': ['MarkdownPage(about)'],
                    'related': {},
                },
                "type": "rss",
            })
            # A feed page renders images, all of a split page, absolute site urls
            rendered = site.pages["index.rss"].render().content()
            self.assertIn(b"src=&#39;https://www.example.org/posts/example-small.jpg", rendered)
            self.assertIn(b"This is the rest of the blog post", rendered)

            self.assertEqual(site.pages["posts/example.jpg"].to_dict(), {
                "src": {
                    "relpath": "posts/example.jpg",
                    "abspath": os.path.join(site.content_root, "posts/example.jpg"),
                },
                'site_path': 'posts/example.jpg',
                "build_path": "posts/example.jpg",
                "meta": {
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'site_name': 'My example blog',
                    'site_url': 'https://www.example.org',
                    'template': 'page.html',
                    'title': 'This is an example image',
                    'width': 500,
                    'height': 477,
                    'nav': ['MarkdownPage(about)'],
                    'related': {
                        'small': 'ScaledImage(posts/example-small.jpg)',
                        'thumbnail': 'ScaledImage(posts/example-thumbnail.jpg)',
                    },
                },
                "type": "image",
            })

            self.assertEqual(site.pages["posts/example-small.jpg"].to_dict(), {
                "src": {
                    "relpath": "posts/example.jpg",
                    "abspath": os.path.join(site.content_root, "posts/example.jpg"),
                },
                'site_path': 'posts/example-small.jpg',
                "build_path": "posts/example-small.jpg",
                "meta": {
                    'created_from': 'Image(posts/example.jpg)',
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'site_name': 'My example blog',
                    'site_url': 'https://www.example.org',
                    'template': 'page.html',
                    'title': 'This is an example image',
                    'width': 480,
                    'height': 458,
                    'nav': ['MarkdownPage(about)'],
                    'related': {},
                },
                "type": "image",
            })

            self.assertEqual(site.pages["posts/example-thumbnail.jpg"].to_dict(), {
                "src": {
                    "relpath": "posts/example.jpg",
                    "abspath": os.path.join(site.content_root, "posts/example.jpg"),
                },
                'site_path': 'posts/example-thumbnail.jpg',
                "build_path": "posts/example-thumbnail.jpg",
                "meta": {
                    'created_from': 'Image(posts/example.jpg)',
                    "date": '2019-06-01 12:30:00+02:00',
                    "draft": False,
                    'author': "Test User",
                    'copyright': '© 2019 Test User',
                    'indexed': False,
                    'syndicated': False,
                    'site_name': 'My example blog',
                    'site_url': 'https://www.example.org',
                    'template': 'page.html',
                    'title': 'This is an example image',
                    'width': 128,
                    'height': 122,
                    'nav': ['MarkdownPage(about)'],
                    'related': {},
                },
                "type": "image",
            })

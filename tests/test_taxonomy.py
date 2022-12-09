from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils
import datetime


class TestTags(test_utils.MockSiteTestMixin, TestCase):
    def test_site(self):
        """
        Test simply assigning pages to taxonomies
        """
        files = {
            "taxonomies/tags.taxonomy": "---\n",
            "page1.md": {"date": str(datetime.datetime(2016, 1, 1)), "tags": ["a", "b"]},
        }
        with self.site(files) as mocksite:
            tags, page1 = mocksite.page("taxonomies/tags", "page1")
            self.assertEqual(tags.categories["a"].pages, [page1])
            self.assertEqual(tags.categories["b"].pages, [page1])

    def test_load(self):
        """
        Test simply assigning pages to taxonomies
        """
        files = {
            "taxonomies/tags.taxonomy": "---\n",
            "page.md": """---
tags: [cat]
---
# Title
"""
        }
        with self.site(files) as mocksite:
            tags, page = mocksite.page("taxonomies/tags", "page")
            cat = tags.categories["cat"]
            self.assertEqual(cat.pages, [page])
            self.assertEqual(page.tags, [cat])

    def test_enrico_tags(self):
        """
        Test tags.taxonomy from my own site
        """
        files = {
            "tags.taxonomy": {
                "title": "All tags",
                "description": "Index of all tags in the site.",
                "category": {
                  "template_title": "Latest posts for tag <strong>{{page.name}}</strong>",
                  "template_description": "Most recent posts with tag <strong>{{page.name}}</strong>",
                  "syndication": {
                    "template_title": "{{page.meta.site_name}}: posts with tag {{page.meta.index.name}}",
                    "template_description": "{{page.meta.site_name}}: most recent posts"
                                            " with tag {{page.meta.index.name}}",
                  }
                },
                "archive": {
                  "template_title": "Archive of posts for tag <strong>{{page.created_from.name}}</strong>",
                  "template_description": "Archive of all posts with tag <strong>{{page.created_from.name}}</strong>",
                },
            },
            "page.md": {
                "tags": ["test", "test1"],
                "title": "Page",
            }
        }
        with self.site(files) as mocksite:
            mocksite.assertPagePaths((
                "", "page", "tags",
                "tags/test", "tags/test/index.rss", "tags/test/index.atom", "tags/test/archive",
                "tags/test1", "tags/test1/index.rss", "tags/test1/index.atom", "tags/test1/archive",
            ))

            page, tags = mocksite.page("page", "tags")
            test, rss, atom, archive = mocksite.page(
                    "tags/test", "tags/test/index.rss", "tags/test/index.atom", "tags/test/archive")
            test1, rss1, atom1, archive1 = mocksite.page(
                    "tags/test1", "tags/test1/index.rss", "tags/test1/index.atom", "tags/test1/archive")

            self.assertEqual(page.title, "Page")
            self.assertIsNone(page.description)
            self.assertEqual(page.tags, [test, test1])
            self.assertEqual(page.related, {})

            self.assertEqual(test.title, "Latest posts for tag <strong>test</strong>")
            self.assertEqual(test.description, "Most recent posts with tag <strong>test</strong>")
            self.assertEqual(test.name, "test")
            self.assertEqual(test.taxonomy, tags)
            self.assertEqual(test.related, {
                "rss_feed": rss,
                "atom_feed": atom,
                "archive": archive,
            })

            self.assertEqual(rss.title, "Test site: posts with tag test")
            self.assertEqual(rss.description, "Test site: most recent posts with tag test")
            self.assertEqual(rss.related, {})
            self.assertEqual(rss.index, test)

            self.assertEqual(archive.title, "Archive of posts for tag <strong>test</strong>")
            self.assertEqual(archive.description, "Archive of all posts with tag <strong>test</strong>")
            self.assertEqual(archive.related, {
                "rss_feed": rss,
                "atom_feed": atom,
            })
            self.assertEqual(archive.index, test)

            self.assertEqual(rss1.title, "Test site: posts with tag test1")
            self.assertEqual(rss1.description, "Test site: most recent posts with tag test1")
            self.assertEqual(rss1.related, {})
            self.assertEqual(rss1.index, test1)

            self.assertEqual(archive1.title, "Archive of posts for tag <strong>test1</strong>")
            self.assertEqual(archive1.description, "Archive of all posts with tag <strong>test1</strong>")
            self.assertEqual(archive1.related, {
                "rss_feed": rss1,
                "atom_feed": atom1,
            })
            self.assertEqual(archive1.index, test1)

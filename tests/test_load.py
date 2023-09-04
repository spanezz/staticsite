from __future__ import annotations
from unittest import TestCase
from . import utils as test_utils


class TestLoad(test_utils.MockSiteTestMixin, TestCase):
    def test_leaf_nodes(self):
        """
        Test that empty leaf nodes are pruned
        """
        files = {
            "index.md": {},
            "drafts/index.md": {"date": "2040-01-01"},
            "skipped/.staticsite": {"skip": True},
            "dir1/dir2/skipped/.staticsite": {"skip": True},
            "dir3/dir4/drafts/index.md": {"date": "2040-01-01"},
            "empty/.gitignore": "",
            "dir5/dir6/empty/.gitignore": "",
        }
        with self.site(files) as mocksite:
            mocksite.assertPagePaths((
                "",
            ))

    def test_ignore(self):
        files = {
            "index.md": {},
            "index.md.swp": {},
            "index.md~": {},
            ".staticsite": {"ignore": ["*.swp", "*~"]},
            "drafts/index.md": {"date": "2040-01-01"},
            "drafts/index.md~": {"date": "2040-01-01"},
            "drafts/index.md.swp": {"date": "2040-01-01"},
        }
        with self.site(files) as mocksite:
            mocksite.assertPagePaths((
                "", "drafts",
            ))

from __future__ import annotations
from staticsite.feature import Feature
import logging

log = logging.getLogger("dir")


class DirPages(Feature):
    """
    Build indices of directory contents.

    When a directory has no index page but contains pages, this will generate
    the index page listing all pages in the directory.
    """
    def finalize(self):
        for dir in self.site.content_roots:
            dir.finalize()


FEATURES = {
    "dirs": DirPages,
}

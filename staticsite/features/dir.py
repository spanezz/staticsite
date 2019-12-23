from __future__ import annotations
from typing import List
from staticsite.site import Site
from staticsite.page import Page
from staticsite.feature import Feature
from staticsite.file import File
from staticsite.utils.typing import Meta
from collections import defaultdict
import os
import logging

log = logging.getLogger("dir")


class DirPages(Feature):
    """
    Build indices of directory contents.

    When a directory has no index page but contains pages, this will generate
    the index page listing all pages in the directory.
    """
    def finalize(self):
        # Group indexable pages by path
        by_dir = defaultdict(list)
        for relpath, page in self.site.pages.items():
            if not page.meta["indexed"]:
                continue
            dir_relpath = os.path.dirname(relpath)
            by_dir[dir_relpath].append(page)

        # Make sure intermediate paths exist
        for path in list(by_dir.keys()):
            while path:
                path = os.path.dirname(path)
                # Do a lookup to create the entry if it does not exist
                by_dir[path]

        # Build directory indices
        dir_pages = []
        for relpath, pages in by_dir.items():
            # We only build indices where there is not already a page
            if relpath in self.site.pages:
                continue
            meta = self.site.dir_meta.get(relpath)
            if meta is None:
                meta = {}
            page = DirPage(self.site, relpath, pages, meta=meta)
            if not page.is_valid():
                log.error("%s: unexpectedly reported page not valid, but we have to add it anyway", page)
            dir_pages.append(page)
            self.site.add_page(page)

        # Add directory indices to their parent directory indices
        for page in dir_pages:
            page.attach_to_parent()

        # Finalize dir_pages from the bottom up
        for page in sorted(dir_pages, key=lambda page: len(page.site_path), reverse=True):
            page.finalize()


class DirPage(Page):
    """
    A directory index
    """
    TYPE = "dir"

    def __init__(self, site: Site, relpath: str, pages: List[Page], meta: Meta):
        super().__init__(
            site=site,
            src=File(relpath=relpath),
            site_path=relpath,
            dst_relpath=os.path.join(relpath, "index.html"),
            meta=meta)

        self.meta.setdefault("template", "dir.html")
        self.meta["pages"] = pages

        if self.src.relpath:
            self.meta["title"] = os.path.basename(self.src.relpath)
        elif self.site.settings.SITE_NAME:
            # If src_relpath is empty, we are the toplevel directory index
            self.meta["title"] = self.site.settings.SITE_NAME
        else:
            # If we have no site name and we need to generate the toplevel
            # directory index, pick a fallback title.
            self.meta["title"] = os.path.dirname(self.site.content_root)

    def attach_to_parent(self):
        # If we are the root, we have nothing to do
        if not self.site_path:
            return

        # Find parent page
        parent_relpath = os.path.dirname(self.site_path)
        parent = self.site.pages[parent_relpath]

        # Set it as meta["parent"]
        self.meta["parent"] = parent

        # Add self to parent directory indices, since we weren't present where
        # the page hierarchy was initially scanned
        if parent.TYPE == "dir":
            parent.meta["pages"].append(self)

    def finalize(self):
        # Set the date as the maximum of the child pages date
        # Since finalize is called from the bottom up, our child pages should
        # all have updated dates
        self.meta["date"] = max(page.meta["date"] for page in self.meta["pages"])


FEATURES = {
    "dirs": DirPages,
}

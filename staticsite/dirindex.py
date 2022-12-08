from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from .page import Page

if TYPE_CHECKING:
    from . import file
    from .site import Site

log = logging.getLogger("dir")


class Dir(Page):
    """
    Page with a directory index
    """
    TYPE = "dir"
    TEMPLATE = "dir.html"

    def __init__(self, site: Site, *, name: Optional[str] = None, **kw):
        super().__init__(site, **kw)
        # Directory name
        self.name: Optional[str] = name
        # Subdirectory of this directory
        self.subdirs: list["Dir"] = []
        # Files found in this directory
        self.files: dict[str, file.File] = {}

        self.syndicated = False
        self.indexed = False

        self.parent: Optional[Page] = None
        if self.node.parent and self.node.parent.page:
            self.parent = self.node.parent.page
            self.title = self.name

        self.subdirs: list[Page] = []

    def analyze(self):
        pages: list[Page] = []
        for name, sub in self.node.sub.items():
            if sub.page and sub.page != self:  # self is always a subpage because of build_as
                if sub.page.directory_index:
                    self.subdirs.append(sub.page)
                else:
                    pages.append(sub.page)
        for name, page in self.node.build_pages.items():
            if page != self and page.leaf and page.meta["indexed"]:
                pages.append(sub.page)

        # FIXME: a lot is here for backwards compatibility. We could do some
        # cleanup, and rearrange theme/default/dir.html accordingly

        self.pages = pages
        # self.meta["indexed"] = bool(self.meta["pages"]) or any(p.meta["indexed"] for p in self.subdirs)

        # TODO: set draft if all subdirs and pages are drafts?

        # Since finalize is called from the bottom up, subdirs have their date
        # up to date
        self.subdirs.sort(key=lambda p: p.meta["date"])
        self.pages.sort(key=lambda p: p.meta["date"])

        date_pages = []
        if self.subdirs:
            date_pages.append(self.subdirs[-1].meta["date"])
        if self.pages:
            date_pages.append(self.meta["pages"][-1].meta["date"])

        if date_pages:
            self.date = max(date_pages)
        else:
            self.date = self.site.localized_timestamp(self.src.stat.st_mtime)

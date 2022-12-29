from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional, Type

from .page import SourcePage, Page, ChangeExtent, TemplatePage
from . import fields

if TYPE_CHECKING:
    from .site import Site

log = logging.getLogger("dir")


class ParentField(fields.Field["Dir", Optional[Page]]):
    """
    Field that works as a proxy for page.node.parent.page
    """
    def __get__(self, page: Page, type: Optional[Type] = None) -> Optional[Page]:
        if (parent := page.node.parent) is None:
            return None
        return parent.page


class Dir(TemplatePage, SourcePage):
    """
    Page with a directory index
    """
    TYPE = "dir"
    TEMPLATE = "dir.html"

    parent = ParentField(doc="Page one level above in the site hierarchy")

    def __init__(self, site: Site, *, name: Optional[str] = None, **kw):
        super().__init__(site, **kw)
        # Directory name
        self.name: Optional[str] = name
        # Subdirectory of this directory
        self.subdirs: list[Page] = []

        self.syndicated = False
        self.indexed = False

        if self.node.parent:
            self.title = self.name

        pages: list[Page] = []
        for name, sub in self.node.sub.items():
            if sub.page:
                if sub.page.directory_index:
                    self.subdirs.append(sub.page)
                else:
                    pages.append(sub.page)
        for name, page in self.node.build_pages.items():
            if page != self and page.leaf and page.indexed:
                pages.append(page)
        pages.sort(key=lambda p: p.date)
        self.pages = pages

        # self.indexed = bool(self.pages) or any(p.indexed for p in self.subdirs)

        # Since finalize is called from the bottom up, subdirs have their date
        # up to date
        self.subdirs.sort(key=lambda p: p.date)

        date_pages = []
        if self.subdirs:
            date_pages.append(self.subdirs[-1].date)
        if self.pages:
            date_pages.append(self.pages[-1].date)

        if date_pages:
            self.date = max(date_pages)
        else:
            self.date = self.site.localized_timestamp(self.src.stat.st_mtime)

    def _compute_change_extent(self) -> ChangeExtent:
        res = super()._compute_change_extent()

        # Check if pages were deleted in this dir
        for relpath in self.site.deleted_source_pages():
            if os.path.dirname(relpath) == self.src.relpath:
                return ChangeExtent.ALL

        # Dir has changed if any page referenced changed in metadata
        for subdir in self.subdirs:
            if subdir.change_extent == ChangeExtent.ALL:
                res = ChangeExtent.ALL
        for page in self.pages:
            if page.change_extent == ChangeExtent.ALL:
                res = ChangeExtent.ALL
        return res

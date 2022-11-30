from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from . import structure
from .page import Page

if TYPE_CHECKING:
    from . import file, scan
    from .site import Site

log = logging.getLogger("dir")


class Dir(Page):
    """
    Page with a directory index
    """
    TYPE = "dir"

    def __init__(self, site: Site, *, name: Optional[str] = None, **kw):
        super().__init__(site, **kw)
        # Directory name
        self.name: Optional[str] = name
        # Subdirectory of this directory
        self.subdirs: list["Dir"] = []
        # Files found in this directory
        self.files: dict[str, file.File] = {}

        if self.node != self.site.structure.root:
            self.meta.setdefault("title", self.name)

        # Parent directory
        self.dir: Optional[Page] = None
        self.subdirs: list[Page] = []

    def analyze(self):
        pages: list[Page] = []
        for name, sub in self.node.sub.items():
            if sub.page and sub.page != self:  # self is always a subpage because of build_as
                if sub.page.directory_index:
                    self.subdirs.append(sub.page)
                else:
                    pages.append(sub.page)

        if self.node.parent and self.node.parent.page:
            self.dir = self.node.parent.page
        else:
            self.dir = self
        self.meta["parent"] = self.dir
        self.meta["pages"] = pages

    @classmethod
    def create(cls, node: structure.Node, directory: scan.Directory):
        return node.create_page(
            page_cls=cls,
            name=node.name,
            directory_index=True,
            src=directory.src,
            build_as=structure.Path(("index.html",)))

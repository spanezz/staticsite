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

        # Pages loaded from this directory
        self.pages = []

    @classmethod
    def create(cls, node: structure.Node, directory: scan.Directory):
        page = cls(node.site, name=node.name, meta=node.meta, src=directory.src)
        node.add_page(page, path=structure.Path(("index.html",)))
        return page

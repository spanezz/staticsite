from __future__ import annotations
from typing import Dict, List, Optional
from .utils.typing import Meta
from . import file
from .page import Page, PageValidationError
from .site import Site
import os
import logging

log = logging.getLogger("contents")


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
        self.subdirs: List["Dir"] = []
        # Files found in this directory
        self.files: Dict[str, file.File] = {}
        # Computed metadata for files and subdirectories
        self.file_meta: Dict[str, Meta] = {}

        # Pages loaded from this directory
        self.pages = []

    def finalize(self):
        # Finalize from the bottom up
        for subdir in self.subdirs:
            subdir.finalize()

        self.meta["pages"] = [p for p in self.pages if not p.meta["draft"]]
        self.meta.setdefault("template", "dir.html")
        self.meta["build_path"] = os.path.join(self.meta["site_path"], "index.html").lstrip("/")

        self.meta["indexed"] = bool(self.meta["pages"]) or any(p.meta["indexed"] for p in self.subdirs)
        self.meta.setdefault("syndicated", False)

        self.meta.setdefault("parent", self.dir)
        if self.dir is not None:
            self.meta["title"] = os.path.basename(self.src.relpath)

        # TODO: set draft if all subdirs and pages are drafts

        # Since finalize is called from the bottom up, subdirs have their date
        # up to date
        self.subdirs.sort(key=lambda p: p.meta["date"])
        self.meta["pages"].sort(key=lambda p: p.meta["date"])

        date_pages = []
        if self.subdirs:
            date_pages.append(self.subdirs[-1].meta["date"])
        if self.meta["pages"]:
            date_pages.append(self.meta["pages"][-1].meta["date"])

        if date_pages:
            self.meta["date"] = max(date_pages)
        else:
            self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)

        if self.meta["indexed"] and self.meta["site_path"] not in self.site.structure.pages:
            self.site.add_page(self)

    def validate(self):
        try:
            super().validate()
        except PageValidationError as e:
            log.error("%s: infrastructural page failed to validate: %s", e.page, e.msg)
            raise

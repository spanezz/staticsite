from __future__ import annotations
from typing import TYPE_CHECKING
from .page import Page
from .render import RenderedFile
import os

if TYPE_CHECKING:
    from .site import Site
    from .utils.typing import Meta
    from .file import File


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site: Site, src: File, meta: Meta, dir=None):
        super().__init__(site=site, src=src, meta=meta, dir=dir)
        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
        self.meta["title"] = os.path.basename(src.relpath)
        self.meta["build_path"] = meta["site_path"]

    def render(self, **kw):
        return {
            self.meta["build_path"]: RenderedFile(self.src),
        }

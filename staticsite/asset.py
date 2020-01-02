from __future__ import annotations
from typing import TYPE_CHECKING
from .page import Page
from .render import RenderedFile
import os

if TYPE_CHECKING:
    from .site import Site
    from .utils.typing import Meta
    from .file import File
    from .contents import Dir


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site: Site, src: File, meta: Meta, dir: Dir, name: str):
        super().__init__(site=site, src=src, meta=meta, dir=dir)
        self.name = name
        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
        self.meta["title"] = name
        self.meta["site_path"] = os.path.join(dir.meta["site_path"], name)
        self.meta["build_path"] = self.meta["site_path"]
        self.meta["asset"] = True

    def render(self, **kw):
        return {
            self.meta["build_path"]: RenderedFile(self.src),
        }

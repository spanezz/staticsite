from __future__ import annotations
from .page import Page
from .render import RenderedFile
from .utils.typing import Meta
from . import site
from .file import File
import os


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site: "site.Site", src: File, site_relpath: str, meta: Meta):
        dirname, basename = os.path.split(src.relpath)

        super().__init__(
            site=site,
            src=src,
            site_relpath=site_relpath,
            dst_relpath=site_relpath,
            meta=meta)

        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
        self.meta["title"] = os.path.basename(src.relpath)

    def render(self):
        return {
            self.dst_relpath: RenderedFile(self.src),
        }

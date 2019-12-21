from .page import Page
from .render import RenderedFile
from .utils.typing import Meta
import os


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site, src, meta: Meta, dest_subdir=None):
        dirname, basename = os.path.split(src.relpath)
        if basename == "index.html":
            linkpath = dirname
        else:
            linkpath = src.relpath

        if dest_subdir:
            dst_relpath = os.path.join(dest_subdir, src.relpath)
            linkpath = os.path.join(dest_subdir, linkpath)
        else:
            dst_relpath = src.relpath

        super().__init__(
            site=site,
            src=src,
            site_relpath=linkpath,
            dst_relpath=dst_relpath,
            meta=meta)

        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
        self.meta["title"] = os.path.basename(src.relpath)

    def render(self):
        return {
            self.dst_relpath: RenderedFile(self.src),
        }

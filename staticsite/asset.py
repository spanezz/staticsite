from .page import Page
from .render import RenderedFile
import os


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site, src, dest_subdir=None, meta=None):
        dirname, basename = os.path.split(src.relpath)
        if basename == "index.html":
            linkpath = dirname
        else:
            linkpath = src.relpath

        if dest_subdir:
            dst_relpath = os.path.join(dest_subdir, src.relpath)
            dst_link = os.path.join(site.settings.SITE_ROOT, dest_subdir, linkpath)
        else:
            dst_relpath = src.relpath
            dst_link = os.path.join(site.settings.SITE_ROOT, linkpath)

        super().__init__(
            site=site,
            src=src,
            src_linkpath=linkpath,
            dst_relpath=dst_relpath,
            dst_link=dst_link,
            meta=meta)

        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
        self.meta["title"] = os.path.basename(src.relpath)

    def render(self):
        return {
            self.dst_relpath: RenderedFile(self.src),
        }

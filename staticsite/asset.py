from .page import Page
from .render import RenderedFile
import datetime
import os
import pytz


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site, src):
        dirname, basename = os.path.split(src.relpath)
        if basename == "index.html":
            linkpath = dirname
        else:
            linkpath = src.relpath

        super().__init__(
            site=site,
            src=src,
            src_linkpath=linkpath,
            dst_relpath=src.relpath,
            dst_link=os.path.join(site.settings.SITE_ROOT, linkpath))

        dt = datetime.datetime.utcfromtimestamp(self.src.stat.st_mtime).replace(tzinfo=pytz.utc)
        self.meta["date"] = dt
        self.meta["title"] = os.path.basename(src.relpath)

    def render(self):
        return {
            self.dst_relpath: RenderedFile(self.src),
        }

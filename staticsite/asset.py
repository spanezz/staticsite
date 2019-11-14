from .page import Page
from .render import RenderedFile, FSFile
import datetime
import os
import pytz


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site, root_abspath, relpath):
        dirname, basename = os.path.split(relpath)
        if basename == "index.html":
            linkpath = dirname
        else:
            linkpath = relpath

        super().__init__(
            site=site,
            root_abspath=root_abspath,
            src_relpath=relpath,
            src_linkpath=linkpath,
            dst_relpath=relpath,
            dst_link=os.path.join(site.settings.SITE_ROOT, linkpath))
        self.title = os.path.basename(relpath)
        self.src = FSFile(self.src_abspath, os.stat(self.src_abspath))

        dt = datetime.datetime.utcfromtimestamp(self.src.stat.st_mtime).replace(tzinfo=pytz.utc)
        self.meta["date"] = dt

    def render(self):
        return {
            self.dst_relpath: RenderedFile(self.src),
        }

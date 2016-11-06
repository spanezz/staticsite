# coding: utf-8

from .core import Page, RenderedFile
import datetime
import os
import pytz
import shutil


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

        dt = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(self.src_abspath)))
        self.meta["date"] = dt

    def render(self):
        return {
            self.dst_relpath: RenderedFile(self.src_abspath),
        }

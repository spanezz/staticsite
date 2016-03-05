# coding: utf-8

from .core import Page, RenderedFile, settings
import os
import shutil


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site, root_abspath, relpath):
        super().__init__(
            site=site,
            root_abspath=root_abspath,
            src_relpath=relpath,
            src_linkpath=relpath,
            dst_relpath=relpath,
            dst_link=os.path.join(settings.SITE_ROOT, relpath))
        self.title = os.path.basename(relpath)

    def render(self):
        return {
            self.dst_relpath: RenderedFile(self.src_abspath),
        }

# coding: utf-8

from .core import Page, RenderedFile
import os
import shutil


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site, root_abspath, relpath):
        super().__init__(site, root_abspath, relpath)
        self.title = os.path.basename(relpath)

    def render(self):
        return {
            self.dst_relpath: RenderedFile(self.src_abspath),
        }

# coding: utf-8

from .core import Page
import os
import shutil

class Asset(Page):
    TYPE = "asset"

    def __init__(self, site, relpath):
        super().__init__(site, relpath)
        self.title = os.path.basename(relpath)

    def write(self, writer):
        dst = writer.output_abspath(self.dst_relpath)
        shutil.copy2(os.path.join(self.site.root, self.src_relpath), dst)

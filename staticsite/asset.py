# coding: utf-8

from .core import Page, RenderedFile
import os
import shutil


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site, relpath):
        super().__init__(site, relpath)
        self.title = os.path.basename(relpath)

    def render(self):
        return {
            self.dst_relpath: RenderedFile(os.path.join(self.site.site_root, self.src_relpath)),
        }


class ThemeAsset(Page):
    TYPE = "asset"

    def __init__(self, site, relpath, theme_assets_relpath):
        super().__init__(site, relpath)
        self.theme_assets_relpath = theme_assets_relpath
        self.title = os.path.basename(relpath)

    def render(self):
        return {
            self.dst_relpath: RenderedFile(os.path.join(self.site.root, self.theme_assets_relpath, self.src_relpath)),
        }

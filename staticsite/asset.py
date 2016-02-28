# coding: utf-8

from .core import Page
import os

class Asset(Page):
    TYPE = "asset"

    def __init__(self, site, relpath):
        super().__init__(site, relpath)
        self.title = os.path.basename(relpath)

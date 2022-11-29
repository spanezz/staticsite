from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .metadata import Meta
from .page import Page
from .render import RenderedElement, RenderedFile

if TYPE_CHECKING:
    from . import file
    from .site import Site


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site: Site, *, name: str, **kw):
        super().__init__(site, **kw)
        self.name = name

    @classmethod
    def create(cls, *, site: Site, src: file.File, parent_meta: Meta, name: str) -> Asset:
        """
        Create an asset, shortcutting metadata derivation
        """
        site_path = os.path.join(parent_meta["site_path"], name)
        meta = parent_meta.derive()
        meta["date"] = site.localized_timestamp(src.stat.st_mtime)
        meta["title"] = name
        meta["site_path"] = site_path
        meta["site_url"] = parent_meta["site_url"]
        meta["asset"] = True
        meta["draft"] = False
        meta["indexed"] = False
        return cls(site=site, meta=meta, src=src, name=name)

    def validate(self):
        # Disable the default page validation: the constructor does all that is
        # needed
        pass

    def render(self, **kw) -> RenderedElement:
        return RenderedFile(self.src)

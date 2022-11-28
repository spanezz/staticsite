from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .page import Page
from .render import RenderedElement, RenderedFile

if TYPE_CHECKING:
    from . import file
    from .site import Site
    from .utils.typing import Meta


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
        meta = {
            "date": site.localized_timestamp(src.stat.st_mtime),
            "title": name,
            "site_url": parent_meta["site_url"],
            "site_path": site_path,
            "asset": True,
            "draft": False,
            "indexed": False,
        }
        return cls(site=site, meta=meta, src=src, name=name)

    def validate(self):
        # Disable the default page validation: the constructor does all that is
        # needed
        pass

    def render(self, **kw) -> RenderedElement:
        return RenderedFile(self.src)

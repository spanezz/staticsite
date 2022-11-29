from __future__ import annotations

from typing import TYPE_CHECKING

from .page import Page
from .render import RenderedElement, RenderedFile

if TYPE_CHECKING:
    from . import file
    from .site import Site


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site: Site, *, src: file.File, name: str, **kw):
        super().__init__(site, src=src, **kw)
        self.meta["date"] = site.localized_timestamp(src.stat.st_mtime)
        self.meta["title"] = name
        self.meta["asset"] = True
        self.meta["draft"] = False
        self.meta["indexed"] = False
        self.name = name

    def validate(self):
        # Disable the default page validation: the constructor does all that is
        # needed
        pass

    def render(self, **kw) -> RenderedElement:
        return RenderedFile(self.src)

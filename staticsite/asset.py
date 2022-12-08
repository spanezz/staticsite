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
        self.date = site.localized_timestamp(src.stat.st_mtime)
        self.title = name
        self.asset = True
        self.draft = False
        self.indexed = False
        self.name = name
        self.ready_to_render = True

    def validate(self):
        # Disable the default page validation: the constructor does all that is
        # needed
        pass

    def render(self, **kw) -> RenderedElement:
        return RenderedFile(self.src)

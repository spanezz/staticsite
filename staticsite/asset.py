from __future__ import annotations

from typing import TYPE_CHECKING

from .page import SourcePage
from .render import RenderedElement, RenderedFile

if TYPE_CHECKING:
    from .site import Site


class Asset(SourcePage):
    TYPE = "asset"

    def __init__(self, site: Site, *, name: str, **kw):
        super().__init__(site, **kw)
        self.date = site.localized_timestamp(self.src.stat.st_mtime)
        self.title = name
        self.asset = True
        self.draft = False
        self.indexed = False
        self.name = name
        self.ready_to_render = True

    def render(self, **kw) -> RenderedElement:
        return RenderedFile(self.src)

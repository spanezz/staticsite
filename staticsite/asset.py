from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .page import Page
from .render import RenderedFile

if TYPE_CHECKING:
    from .site import Site


class Asset(Page):
    TYPE = "asset"

    def __init__(self, site: Site, *, name: str, **kw):
        super().__init__(site, **kw)
        self.name = name
        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
        self.meta["title"] = name
        self.meta["site_url"] = self.src_dir.meta["site_url"]
        self.meta["site_path"] = os.path.join(self.src_dir.meta["site_path"], name)
        self.meta["build_path"] = self.meta["site_path"].lstrip("/")
        self.meta["asset"] = True
        self.meta["draft"] = False
        self.meta["indexed"] = False

    def validate(self):
        # Disable the default page validation: the constructor does all that is
        # needed
        pass

    def render(self, **kw):
        return {
            self.meta["build_path"]: RenderedFile(self.src),
        }

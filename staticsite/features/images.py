from __future__ import annotations
from typing import List
from staticsite import Page, Feature, File, Site
from staticsite.contents import ContentDir, Dir
from staticsite.render import RenderedFile
from staticsite.utils.typing import Meta
import os
import mimetypes
import logging

log = logging.getLogger("images")


class Images(Feature):
    """
    Handle images in content directory.

    See doc/reference/images.md for details.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        mimetypes.init()

    def load_dir(self, sitedir: ContentDir) -> List[Page]:
        taken: List[str] = []
        pages: List[Page] = []
        for fname, src in sitedir.files.items():
            base, ext = os.path.splitext(fname)
            mimetype = mimetypes.types_map.get(ext)
            if mimetype is None:
                continue

            if not mimetype.startswith("image/"):
                continue

            meta = sitedir.meta_file(fname)
            meta["site_path"] = os.path.join(meta["site_path"], fname)

            page = Image(self.site, src, meta=meta, dir=sitedir, mimetype=mimetype)
            pages.append(page)

        for fname in taken:
            del sitedir.files[fname]

        return pages


class Image(Page):
    TYPE = "image"

    def __init__(self, site: Site, src: File, meta: Meta, dir: Dir = None, mimetype: str = None):
        super().__init__(site=site, src=src, meta=meta, dir=dir)
        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
        self.meta["title"] = os.path.basename(src.relpath)
        self.meta["build_path"] = meta["site_path"]

    def render(self, **kw):
        return {
            self.meta["build_path"]: RenderedFile(self.src),
        }


FEATURES = {
    "images": Images,
}

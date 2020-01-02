from __future__ import annotations
from typing import List, Dict
from staticsite import Page, Feature, File, Site
from staticsite.contents import ContentDir, Dir
from staticsite.render import RenderedFile
from staticsite.utils.typing import Meta
from staticsite.utils.images import ImageScanner
from staticsite.metadata import Metadata
import os
import mimetypes
import logging

log = logging.getLogger("images")


class MetadataImage(Metadata):
    def __init__(self, images: "Images", *args, **kw):
        super().__init__(*args, **kw)
        # Store a reference to the Images feature
        self.images = images

    def on_analyze(self, page: Page):
        val = page.meta.get(self.name)
        if val is None:
            val = self.images.by_related_site_path.get(page.meta["site_path"])
            if val is not None:
                page.meta[self.name] = val
        elif isinstance(val, str):
            val = page.resolve_path(val)
            page.meta[self.name] = val


class Images(Feature):
    """
    Handle images in content directory.

    See doc/reference/images.md for details.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        mimetypes.init()
        self.scanner = ImageScanner(self.site.caches.get("images_meta"))
        self.site.register_metadata(MetadataImage(self, "image", doc="""
Image used for this post.

It is set to a path to an image file relative to the current page.

During the analyze phase, it is resolved to the corresponding [image page](images.md).

If not set, and an image exists with the same name as the page (besides the
extension), that image is used.
"""))
        # Index images by the site path a related article would have
        self.by_related_site_path: Dict[str, "Image"] = {}

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

            taken.append(fname)

            meta = sitedir.meta_file(fname)
            related_site_path = os.path.join(sitedir.meta["site_path"], base)
            meta["site_path"] = os.path.join(sitedir.meta["site_path"], fname)

            img_meta = self.scanner.scan(sitedir, src, mimetype)
            meta.update(img_meta)

            page = Image(self.site, src, meta=meta, dir=sitedir, mimetype=mimetype)
            pages.append(page)

            self.by_related_site_path[related_site_path] = page

        for fname in taken:
            del sitedir.files[fname]

        return pages


class Image(Page):
    TYPE = "image"

    def __init__(self, site: Site, src: File, meta: Meta, dir: Dir = None, mimetype: str = None):
        super().__init__(site=site, src=src, meta=meta, dir=dir)
        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
        self.meta["build_path"] = meta["site_path"]

    def render(self, **kw):
        return {
            self.meta["build_path"]: RenderedFile(self.src),
        }


FEATURES = {
    "images": Images,
}

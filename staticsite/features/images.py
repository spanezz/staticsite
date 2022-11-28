from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict
from staticsite import Page, Feature
from staticsite.render import RenderedFile
from staticsite.utils.typing import Meta
from staticsite.utils.images import ImageScanner
from staticsite.metadata import Metadata
from staticsite.render import RenderedElement
import os
import mimetypes
import logging

if TYPE_CHECKING:
    from staticsite import file, scan

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

    def load_dir(self, sourcedir: scan.SourceDir, files: dict[str, tuple[Meta, file.File]]) -> List[Page]:
        taken: List[str] = []
        pages: List[Page] = []
        for fname, (meta, src) in files.items():
            base, ext = os.path.splitext(fname)
            mimetype = mimetypes.types_map.get(ext)
            if mimetype is None:
                continue

            if not mimetype.startswith("image/"):
                continue

            taken.append(fname)

            related_site_path = os.path.join(sourcedir.meta["site_path"], base)
            meta["site_path"] = os.path.join(sourcedir.meta["site_path"], fname)

            img_meta = self.scanner.scan(sourcedir, src, mimetype)
            meta.update(img_meta)

            page = Image(self.site, src=src, meta=meta, dir=sourcedir, mimetype=mimetype)
            pages.append(page)

            # Look at theme's image_sizes and generate ScaledImage pages
            image_sizes = self.site.theme.meta.get("image_sizes")
            if image_sizes:
                for name, info in image_sizes.items():
                    width = meta.get("width")
                    if width is None:
                        # SVG images, for example, don't have width
                        continue
                    if info["width"] >= width:
                        continue
                    rel_meta = dict(meta)
                    rel_meta["related"] = {}
                    rel_meta.pop("width", None)
                    rel_meta.pop("height", None)
                    rel_meta.update(**info)
                    scaled = ScaledImage.create_from(page, rel_meta, mimetype=mimetype, name=name, info=info)
                    pages.append(scaled)

            self.by_related_site_path[related_site_path] = page

        for fname in taken:
            del files[fname]

        return pages


class Image(Page):
    TYPE = "image"

    def __init__(self, *args, mimetype: str = None, **kw):
        super().__init__(*args, **kw)
        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
        self.meta["build_path"] = self.meta["site_path"]

    def render(self, **kw):
        return {
            self.meta["build_path"]: RenderedFile(self.src),
        }


class RenderedScaledImage(RenderedElement):
    def __init__(self, src: file.File, width: int, height: int):
        self.src = src
        self.width = width
        self.height = height

    def write(self, dst: file.File):
        import PIL
        with PIL.Image.open(self.src.abspath) as img:
            img = img.resize((self.width, self.height))
            img.save(dst.abspath)

    def content(self):
        with open(self.src.abspath, "rb") as fd:
            return fd.read()


class ScaledImage(Page):
    TYPE = "image"

    def __init__(self, *args, mimetype: str = None, name: str = None, info: Meta = None, **kw):
        super().__init__(*args, **kw)
        self.name = name
        self.meta["date"] = self.created_from.meta["date"]

        site_path = self.created_from.meta["site_path"]
        base, ext = os.path.splitext(site_path)
        site_path = f"{base}-{name}{ext}"
        self.meta["site_path"] = site_path
        self.meta["build_path"] = site_path

        if "height" not in self.meta:
            self.meta["height"] = round(
                    self.created_from.meta["height"] * (
                        info["width"] / self.created_from.meta["width"]))

        self.created_from.add_related(name, self)

    def render(self, **kw):
        return {
            self.meta["build_path"]: RenderedScaledImage(self.src, self.meta["width"], self.meta["height"]),
        }


FEATURES = {
    "images": Images,
}

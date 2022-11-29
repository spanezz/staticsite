from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict
from staticsite import Page, Feature, structure
from staticsite.render import RenderedFile
from staticsite.utils.images import ImageScanner
from staticsite.metadata import Metadata
from staticsite.render import RenderedElement
import os
import mimetypes
import logging

if TYPE_CHECKING:
    from staticsite import file, scan
    from staticsite.metadata import Meta

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

    def load_dir(
            self,
            node: structure.Node,
            directory: scan.Directory,
            files: dict[str, tuple[Meta, file.File]]) -> list[Page]:
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

            related_site_path = os.path.join(directory.meta["site_path"], base)

            img_meta = self.scanner.scan(src, mimetype)
            meta.update(img_meta)

            page = Image(self.site, src=src, meta=meta, mimetype=mimetype)
            pages.append(page)

            page.meta["site_path"] = os.path.join(directory.meta["site_path"], fname)
            page.meta["build_path"] = page.meta["site_path"]
            node.add_page(page, src=src, path=structure.Path(fname))

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
                    rel_meta = meta.derive()
                    rel_meta["related"] = {}
                    rel_meta.pop("width", None)
                    rel_meta.pop("height", None)
                    rel_meta.update(info)
                    scaled = ScaledImage.create_from(page, rel_meta, mimetype=mimetype, name=name, info=info)
                    pages.append(scaled)

                    site_path = scaled.created_from.meta["site_path"]
                    base, ext = os.path.splitext(site_path)
                    site_path = f"{base}-{name}{ext}"
                    scaled.meta["site_path"] = site_path
                    self.site.structure.add_generated_page(scaled, site_path)

            self.by_related_site_path[related_site_path] = page

        for fname in taken:
            del files[fname]

        return pages


class Image(Page):
    TYPE = "image"

    def __init__(self, *args, mimetype: str = None, **kw):
        super().__init__(*args, **kw)
        self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)

    def render(self, **kw) -> RenderedElement:
        return RenderedFile(self.src)


class RenderedScaledImage(RenderedElement):
    def __init__(self, src: file.File, width: int, height: int):
        self.src = src
        self.width = width
        self.height = height

    def write(self, name: str, dir_fd: int):
        import PIL
        with PIL.Image.open(self.src.abspath) as img:
            img = img.resize((self.width, self.height))
            with self.dirfd_open(name, "wb", dir_fd=dir_fd) as out:
                img.save(out)

    def content(self):
        with open(self.src.abspath, "rb") as fd:
            return fd.read()


class ScaledImage(Page):
    TYPE = "image"

    def __init__(self, *args, mimetype: str = None, name: str = None, info: Meta = None, **kw):
        super().__init__(*args, **kw)
        self.name = name
        self.meta["date"] = self.created_from.meta["date"]

        if "height" not in self.meta:
            self.meta["height"] = round(
                    self.created_from.meta["height"] * (
                        info["width"] / self.created_from.meta["width"]))

        self.created_from.add_related(name, self)

    def render(self, **kw) -> RenderedElement:
        return RenderedScaledImage(self.src, self.meta["width"], self.meta["height"])


FEATURES = {
    "images": Images,
}

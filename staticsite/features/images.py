from __future__ import annotations
from typing import TYPE_CHECKING, Any
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
            if (parent := page.node.parent) is None:
                return
            if parent not in self.images.nodes_with_images:
                return
            # Look for sibling pages that are images, that share the file name
            # without extension
            prefix = page.node.name + "."
            for name, subnode in parent.sub.items():
                if not name.startswith(prefix):
                    continue
                if not subnode.page:
                    continue
                if not isinstance(subnode.page, Image):
                    continue
                page.meta[self.name] = subnode.page
                break
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
        # Nodes that contain images
        self.nodes_with_images: set[structure.Node] = set()

    def load_dir(
            self,
            node: structure.Node,
            directory: scan.Directory,
            files: dict[str, tuple[dict[str, Any], file.File]]) -> list[Page]:
        taken: list[str] = []
        pages: list[Page] = []
        for fname, (meta_values, src) in files.items():
            base, ext = os.path.splitext(fname)
            mimetype = mimetypes.types_map.get(ext)
            if mimetype is None:
                continue

            if not mimetype.startswith("image/"):
                continue

            taken.append(fname)

            img_meta = self.scanner.scan(src, mimetype)
            meta_values.update(img_meta)

            page = node.create_page(
                page_cls=Image,
                src=src,
                meta_values=meta_values,
                mimetype=mimetype,
                path=structure.Path((fname,)))
            pages.append(page)

            # Look at theme's image_sizes and generate ScaledImage pages
            image_sizes = self.site.theme.meta.get("image_sizes")
            if image_sizes:
                for name, info in image_sizes.items():
                    width = meta_values.get("width")
                    if width is None:
                        # SVG images, for example, don't have width
                        continue
                    if info["width"] >= width:
                        continue
                    rel_meta = {}
                    rel_meta["related"] = {}
                    rel_meta["width"] = None
                    rel_meta["height"] = None
                    rel_meta.update(info)

                    base, ext = os.path.splitext(fname)
                    scaled_fname = f"{base}-{name}{ext}"

                    scaled = node.create_page(
                        page_cls=ScaledImage,
                        created_from=page,
                        meta_values=rel_meta,
                        mimetype=mimetype,
                        name=name,
                        info=info,
                        path=structure.Path((scaled_fname,)))
                    pages.append(scaled)

            self.nodes_with_images.add(node)

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

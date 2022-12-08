from __future__ import annotations

import itertools
import logging
import mimetypes
import os
from typing import TYPE_CHECKING, Any

from staticsite import Feature, Page, fields, structure
from staticsite.metadata import FieldsMetaclass
from staticsite.render import RenderedElement, RenderedFile
from staticsite.utils.images import ImageScanner

if TYPE_CHECKING:
    from staticsite import file, scan

log = logging.getLogger("images")


def basename_no_ext(pathname: str) -> str:
    """
    Return the basename of pathname, without extension
    """
    return os.path.splitext(os.path.basename(pathname))[0]


class ImagePageMixin(metaclass=FieldsMetaclass):
    image = fields.Field(doc="""
        Image used for this post.

        It is set to a path to an image file relative to the current page.

        During the analyze phase, it is resolved to the corresponding [image page](images.md).

        If not set, and an image exists with the same name as the page (besides the
        extension), that image is used.
    """)


class Images(Feature):
    """
    Handle images in content directory.

    See doc/reference/images.md for details.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        mimetypes.init()
        self.scanner = ImageScanner(self.site.caches.get("images_meta"))
        self.page_mixins.append(ImagePageMixin)
        self.site.structure.add_tracked_metadata("image")
        # Nodes that contain images
        self.images: set[Image] = set()

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
                dst=fname)
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
                    rel_meta = dict(info)
                    rel_meta["related"] = {}

                    base, ext = os.path.splitext(fname)
                    scaled_fname = f"{base}-{name}{ext}"

                    scaled = node.create_page(
                        page_cls=ScaledImage,
                        src=src,
                        created_from=page,
                        meta_values=rel_meta,
                        mimetype=mimetype,
                        name=name,
                        info=info,
                        dst=scaled_fname)
                    pages.append(scaled)

            self.images.add(page)

        for fname in taken:
            del files[fname]

        return pages

    def analyze(self):
        # Resolve image from strings to Image pages
        for page in self.site.structure.pages_by_metadata["image"]:
            val = page.meta.get(self.name)
            if isinstance(val, str):
                val = page.resolve_path(val)
                # TODO: warn if val is not an Image page?
                page.meta[self.name] = val

        # If an image exists with the same basename as a page, auto-add an
        # "image" metadata to it
        for image in self.images:
            name = basename_no_ext(image.src.relpath)
            # print(f"Images.analyze {image=!r} {image.node.name=!r} {image.node.page=!r}")
            pages = image.node.build_pages.values()
            if image.node.sub is not None:
                pages = itertools.chain(pages, (subnode.page for subnode in image.node.sub.values() if subnode.page))

            # Find pages matching this image's name
            for page in pages:
                # print(f"Images.analyze  check {page=!r} {page.src=!r}")
                if not (src := page.src):
                    # Don't associate to generated pages
                    continue
                if (page.src.relpath == image.src.relpath):
                    # Don't associate to variants of this image
                    continue
                if basename_no_ext(src.relpath) == name:
                    # Don't add if already set
                    if not page.meta.get("image") and basename_no_ext(src.relpath) == name:
                        # print("Images.analyze  add")
                        page.meta["image"] = image
                    break


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
        # if os.access(name, dir_fd=dir_fd, mode=os.W_OK):
        #     return
        # TODO: if target exists and mtime is ok, keep it
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

    def __init__(self, *args, mimetype: str = None, name: str = None, info: dict[str, Any] = None, **kw):
        super().__init__(*args, **kw)
        self.name = name
        created_from = self.meta["created_from"]
        self.meta["date"] = created_from.meta["date"]
        if (title := created_from.meta.get("title")):
            self.meta["title"] = title

        if "height" not in self.meta:
            self.meta["height"] = round(
                    created_from.meta["height"] * (
                        info["width"] / created_from.meta["width"]))

        self.created_from.add_related(name, self)

    def render(self, **kw) -> RenderedElement:
        return RenderedScaledImage(self.src, self.meta["width"], self.meta["height"])


FEATURES = {
    "images": Images,
}

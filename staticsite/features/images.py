from __future__ import annotations

import itertools
import logging
import mimetypes
import os
from typing import TYPE_CHECKING, Any, Optional

from staticsite import fields
from staticsite.feature import Feature, TrackedFieldMixin, PageTrackingMixin
from staticsite.page import SourcePage, AutoPage, Page, ChangeExtent
from staticsite.render import RenderedElement, RenderedFile
from staticsite.utils.images import ImageScanner

if TYPE_CHECKING:
    from staticsite import file, scan
    from staticsite.node import Node

log = logging.getLogger("images")


def basename_no_ext(pathname: str) -> str:
    """
    Return the basename of pathname, without extension
    """
    return os.path.splitext(os.path.basename(pathname))[0]


class ImageField(TrackedFieldMixin, fields.Field):
    """
    Image used for this post.

    It is set to a path to an image file relative to the current page.

    During the crossreference phase, it is resolved to the corresponding
    [image page](images.md).

    If not set, and an image exists with the same name as the page (besides the
    extension), that image is used.
    """
    tracked_by = "images"


class ImagePageMixin(metaclass=fields.FieldsMetaclass):
    image = ImageField()
    width = fields.Field(doc="""
        Image width
    """)
    height = fields.Field(doc="""
        Image height
    """)


class Images(PageTrackingMixin, Feature):
    """
    Handle images in content directory.

    See doc/reference/images.md for details.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        mimetypes.init()
        self.scanner = ImageScanner(self.site.caches.get("images_meta"))
        self.page_mixins.append(ImagePageMixin)
        # Nodes that contain images
        self.images: set[Image] = set()

    def load_dir(
            self,
            node: Node,
            directory: scan.Directory,
            files: dict[str, tuple[dict[str, Any], file.File]]) -> list[Page]:
        taken: list[str] = []
        pages: list[Page] = []
        for fname, (kwargs, src) in files.items():
            base, ext = os.path.splitext(fname)
            mimetype = mimetypes.types_map.get(ext)
            if mimetype is None:
                continue

            if not mimetype.startswith("image/"):
                continue

            taken.append(fname)

            img_meta = self.scanner.scan(src, mimetype)
            kwargs.update(img_meta)

            page = node.create_source_page(
                page_cls=Image,
                src=src,
                mimetype=mimetype,
                dst=fname,
                **kwargs)
            pages.append(page)

            # Look at theme's image_sizes and generate ScaledImage pages
            image_sizes = self.site.theme.meta.get("image_sizes")
            if image_sizes:
                for name, info in image_sizes.items():
                    width = kwargs.get("width")
                    if width is None:
                        # SVG images, for example, don't have width
                        continue
                    if info["width"] >= width:
                        continue
                    rel_kwargs = dict(info)
                    rel_kwargs["related"] = {}

                    base, ext = os.path.splitext(fname)
                    scaled_fname = f"{base}-{name}{ext}"

                    scaled = node.create_auto_page(
                        page_cls=ScaledImage,
                        created_from=page,
                        mimetype=mimetype,
                        name=name,
                        info=info,
                        dst=scaled_fname,
                        **rel_kwargs)
                    pages.append(scaled)

            self.images.add(page)

        for fname in taken:
            del files[fname]

        return pages

    def crossreference(self):
        # Resolve image from strings to Image pages
        for page in self.tracked_pages:
            val = page.image
            if isinstance(val, str):
                page.image = page.resolve_path(val)
                if page.image.TYPE != "image":
                    log.warning("%s: image field resolves to %s which is not an image page",
                                self, page.image)

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
                    if not page.image and basename_no_ext(src.relpath) == name:
                        # print(f"Images.analyze  add {image!r}")
                        page.image = image
                    break


class Image(SourcePage):
    TYPE = "image"

    lat = fields.Field(doc="Image latitude")
    lon = fields.Field(doc="Image longitude")
    image_orientation = fields.Field(doc="Image orientation")

    def __init__(self, *args, mimetype: str = None, **kw):
        super().__init__(*args, **kw)
        # self.date = self.site.localized_timestamp(self.src.stat.st_mtime)

    def render(self, **kw) -> RenderedElement:
        return RenderedFile(self.src)


class RenderedScaledImage(RenderedElement):
    def __init__(self, src: file.File, width: int, height: int):
        self.src = src
        self.width = width
        self.height = height

    def write(self, *, name: str, dir_fd: int, old: Optional[os.stat_result]):
        # If target exists and mtime is ok, keep it
        if old and old.st_mtime >= self.src.stat.st_mtime:
            return
        import PIL
        with PIL.Image.open(self.src.abspath) as img:
            img = img.resize((self.width, self.height))
            with self.dirfd_open(name, "wb", dir_fd=dir_fd) as out:
                img.save(out)

    def content(self):
        with open(self.src.abspath, "rb") as fd:
            return fd.read()


class ScaledImage(AutoPage):
    TYPE = "image"

    def __init__(self, *args, mimetype: str = None, name: str = None, info: dict[str, Any] = None, **kw):
        super().__init__(*args, **kw)
        self.name = name
        created_from = self.created_from
        self.date = created_from.date
        if (title := created_from.title):
            self.title = title

        if self.height is None:
            self.height = round(
                    created_from.height * (
                        info["width"] / created_from.width))

        created_from.add_related(name, self)

    def render(self, **kw) -> RenderedElement:
        return RenderedScaledImage(self.created_from.src, self.width, self.height)

    def _compute_change_extent(self) -> ChangeExtent:
        return self.created_from.change_extent


FEATURES = {
    "images": Images,
}

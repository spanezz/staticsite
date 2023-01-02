from __future__ import annotations

import itertools
import logging
import mimetypes
import os
from typing import TYPE_CHECKING, Any, Optional, Sequence, Type, Union, cast

from staticsite import fields
from staticsite.feature import Feature, PageTrackingMixin, TrackedField
from staticsite.page import AutoPage, ChangeExtent, Page, SourcePage, ImagePage
from staticsite.render import RenderedElement, RenderedFile
from staticsite.utils.images import ImageScanner

if TYPE_CHECKING:
    from staticsite import file, fstree
    from staticsite.source_node import SourcePageNode

log = logging.getLogger("images")


def basename_no_ext(pathname: str) -> str:
    """
    Return the basename of pathname, without extension
    """
    return os.path.splitext(os.path.basename(pathname))[0]


class ImageField(TrackedField[Page, Union[str, "Image"]]):
    """
    Image used for this post.

    It is set to a path to an image file relative to the current page.

    During the crossreference phase, it is resolved to the corresponding
    [image page](images.md).

    If not set, and an image exists with the same name as the page (besides the
    extension), that image is used.
    """
    tracked_by = "images"

    def _clean(self, page: Page, value: Any) -> Union[str, "Image"]:
        if isinstance(value, str):
            return value
        elif isinstance(value, Image):
            return value
        else:
            raise TypeError(
                    f"invalid value of type {type(value)} for {page!r}.{self.name}:"
                    " expecting str or Image")


class ImagePageMixin(Page):
    image = ImageField()


class Images(PageTrackingMixin, Feature):
    """
    Handle images in content directory.

    Files with an `image/*` mime type found in content directories are scanned for
    metadata and used as image pages.

    Their behaviour is similar to the one of static assets, but templates and other
    staticsite facilities can make use of the metadata resolved.


    ## Metadata extracted from images

    These are the current metadata elements filled from image data, when available:

    * `page.meta.width`: image width in pixels
    * `page.meta.height`: image height in pixels
    * `page.meta.lat`: latitude from EXIF tags, as a signed floating point number
      of degrees
    * `page.meta.lon`: longitude from EXIF tags, as a signed floating point number
      of degrees
    * `page.meta.title`: content of the `ImageDescription` EXIF tag
    * `page.meta.author`: content of the `Artist` EXIF tag
    * `page.meta.image_orientation`: content of the
      [`ImageOrientation` EXIF tag](https://www.impulseadventure.com/photo/exif-orientation.html)


    ## Image associated to another page

    If you have an image sharing the file name with another page (for example, an
    image called `example.jpg` next to a page called `example.md`), then the page
    automatically gets a `page.meta.image` value pointing to the image.

    You can use this, for example, to easily provide an image for blog posts.


    ## Scaled versions of images

    [Theme](../theme.md) configurations can specify a set of scaled versions of images
    to generate:

    ```yaml
    # Scaled down widths of images that will be generated
    image_sizes:
      medium:
        width: 600
      small:
        width: 480
      thumbnail:
        width: 128
    ```

    Given a `image.jpg` image file, this will generate `image-medium.jpg`,
    `image-small.jpg` and `image-thumbnail.jpg`.

    Using this feature, the [`img_for` template function](templates.md) will
    automatically generate `srcset` attributes to let the browser choose which
    version to load.

    Scaled versions of the image will be available in the image's [`related`
    field](../fields/related.md).
    """
    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw)
        mimetypes.init()
        self.scanner = ImageScanner(self.site.caches.get("images_meta"))
        # Nodes that contain images
        self.images: set[Image] = set()

    def get_page_bases(self, page_cls: Type[Page]) -> Sequence[Type[Page]]:
        return (ImagePageMixin,)

    def get_used_page_types(self) -> list[Type[Page]]:
        return [Image, ScaledImage]

    def load_dir(
            self,
            node: SourcePageNode,
            directory: fstree.Tree,
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

            page = node.create_source_page_as_file(
                page_cls=Image,
                src=src,
                mimetype=mimetype,
                dst=fname,
                **kwargs)
            pages.append(page)

            self.images.add(page)

        for fname in taken:
            del files[fname]

        return pages

    def generate(self):
        for image in self.images:
            # Look at theme's image_sizes and generate ScaledImage pages
            image_sizes = self.site.theme.meta.get("image_sizes")
            if image_sizes:
                for name, info in image_sizes.items():
                    width = image.width
                    if width is None:
                        # SVG images, for example, don't have width
                        continue
                    if info["width"] >= width:
                        continue
                    rel_kwargs = dict(info)
                    rel_kwargs["related"] = {}

                    base, ext = os.path.splitext(os.path.basename(image.src.relpath))
                    scaled_fname = f"{base}-{name}{ext}"

                    image.node.create_auto_page_as_file(
                        page_cls=ScaledImage,
                        created_from=image,
                        mimetype=image.mimetype,
                        name=name,
                        info=info,
                        dst=scaled_fname,
                        **rel_kwargs)

    def crossreference(self):
        # Resolve image from strings to Image pages
        for page in self.tracked_pages:
            val = page.image
            if isinstance(val, str):
                page.image = page.resolve_path(val)
                if page.image.TYPE not in ("image", "scaledimage"):
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
                if not isinstance(page, SourcePage):
                    # Don't associate to generated pages
                    continue
                if (page.src.relpath == image.src.relpath):
                    # Don't associate to variants of this image
                    continue
                if basename_no_ext(page.src.relpath) == name:
                    # Don't add if already set
                    if not page.image and basename_no_ext(page.src.relpath) == name:
                        # print(f"Images.analyze  add {image!r}")
                        page.image = image
                    break


class Image(ImagePage, SourcePage):
    """
    An image as found in the source directory
    """
    TYPE = "image"

    lat = fields.Float[Page](doc="Image latitude")
    lon = fields.Float[Page](doc="Image longitude")
    image_orientation = fields.Int[Page](doc="Image orientation")

    def __init__(self, *args, mimetype: str, **kw):
        super().__init__(*args, **kw)
        self.mimetype = mimetype
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


class ScaledImage(ImagePage, AutoPage):
    """
    Scaled version of an image
    """
    TYPE = "scaledimage"

    # Note: from Python 3.12, we can parameterize Page on the type of
    # created_from, defaulting to Page: https://peps.python.org/pep-0696/
    #
    # Now if we did that we'd have to specify a third type explicitly every
    # time we describe a page, and it's easier to work around it with cast.
    # With 3.12 we can remove the casts in favour of an extra type in the page
    # definition

    def __init__(self, *args, mimetype: str, name: str, info: dict[str, Any], **kw):
        super().__init__(*args, **kw)
        self.name = name
        created_from = cast(Image, self.created_from)
        self.date = created_from.date
        if (title := created_from.title):
            self.title = title

        if self.height is None:
            self.height = round(
                    created_from.height * (
                        info["width"] / created_from.width))

        created_from.add_related(name, self)

    def render(self, **kw) -> RenderedElement:
        return RenderedScaledImage(cast(Image, self.created_from).src, self.width, self.height)

    def _compute_change_extent(self) -> ChangeExtent:
        return self.created_from.change_extent


FEATURES = {
    "images": Images,
}

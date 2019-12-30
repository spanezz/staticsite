# Images

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
* `page.meta.image_orientation`: content of the [`ImageOrientation` EXIF tag](https://www.impulseadventure.com/photo/exif-orientation.html)


## Image associated to another page

If you have an image sharing the file name with another page (for example, an
image called `example.jpg` next to a page called `example.md`), then the page
automatically gets a `page.meta.image` value pointing to the image.

You can use this, for example, to easily provide an image for blog posts.

[Back to reference index](README.md)
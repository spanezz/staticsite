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


## Scaled versions of images

[Theme](theme.md) configurations can specify a set of scaled versions of images
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

Scaled versions of the image will be available in the image's [`meta.related`
metadata](metadata.md#related).

[Back to reference index](README.md)

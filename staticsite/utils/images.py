from __future__ import annotations
from typing import TYPE_CHECKING, List
import PIL
import PIL.Image
import subprocess
import json
import shlex
import os
import logging

if TYPE_CHECKING:
    from staticsite.contents import ContentDir
    from staticsite import File
    from staticsite.cache import Cache
    from .typing import Meta

log = logging.getLogger("utils.images")


def parse_coord(ref, vals):
    vdeg, vmin, vsec = vals

    val = vdeg[0] / vdeg[1] + vmin[0] / (vmin[1] * 60) + vsec[0] / (vsec[1] * 3600)

    if ref in ("S", "W"):
        return -val
    else:
        return val


class ImageScanner:
    def __init__(self, cache: Cache):
        self.cache = cache

    def scan(self, sitedir: ContentDir, src: File, mimetype: str) -> Meta:
        key = f"{src.abspath}:{src.stat.st_mtime:.3f}"
        meta = self.cache.get(key)
        if meta is None:
            meta = self.read_meta(src.abspath, mimetype)
            self.cache.put(key, meta)
        return meta

    def scan_file(self, pathname: str) -> Meta:
        import mimetypes
        mimetypes.init()
        base, ext = os.path.splitext(pathname)
        mimetype = mimetypes.types_map.get(ext)
        if mimetype is None:
            return {}
        return self.read_meta(pathname, mimetype)

    def read_meta(self, pathname: str, mimetype: str) -> Meta:
        # We can take our time here, since results are cached

        if mimetype == "image/svg+xml":
            return {}

        with PIL.Image.open(pathname) as img:
            meta = {
                "width": img.width,
                "height": img.height,
                "title": "",
            }

            meta.update(self.read_meta_exiftool(pathname))

        return meta

    def read_meta_exiftool(self, pathname: str) -> Meta:
        meta = {}

        # It is important to use abspath here, as exiftool does not support the
        # usual -- convention to deal with files starting with a dash. With abspath
        # at least the file name will start with a /
        res = subprocess.run(["exiftool", "-json", "-n", "-c", "%f", pathname], capture_output=True)
        if res.returncode != 0:
            log.warn("%s: exiftool failed with code %d: %s", pathname, res.returncode, res.stderr.strip())
            return meta

        info = json.loads(res.stdout)[0]

        description = info.get("ImageDescription")
        if description is not None:
            meta["title"] = description

        artist = info.get("Artist")
        if artist is not None:
            meta["author"] = artist

        orientation = info.get("Orientation")
        if orientation is not None:
            # https://www.impulseadventure.com/photo/exif-orientation.html
            meta["image_orientation"] = int(orientation)

        copyright = info.get("CopyrightNotice")
        if copyright is not None:
            meta["copyright"] = copyright

        lat = info.get("GPSLatitude")
        if lat is not None:
            meta["lat"] = float(lat)

        lon = info.get("GPSLongitude")
        if lon is not None:
            meta["lon"] = float(lon)

        # "DateTime": "2017:05:09 21:27:42",
        # "GPSLatitudeRef": "North",
        # "GPSAltitude": "92 m",
        # "GPSTimeStamp": "19:27:43",
        # "GPSDateStamp": "2017:05:09",
        # "GPSDateTime": "2017:05:09 19:27:43Z",

        return meta

    def edit_meta_exiftool(self, pathname: str, changed: Meta, removed: List[str]):
        exif_args: List[str] = []

        if "title" in changed:
            exif_args.append(f"-ImageDescription={changed['title']}")

        if "author" in changed:
            exif_args.append(f"-Artist={changed['author']}")

        if "image_orientation" in changed:
            exif_args.append(f"-Orientation={changed['image_orientation']}")

        if "copyright" in changed:
            # See https://libre-software.net/edit-metadata-exiftool/
            exif_args.append(f"-rights={changed['copyright']}")
            exif_args.append(f"-CopyrightNotice={changed['copyright']}")

        # lat = info.get("GPSLatitude")
        # if lat is not None:
        #     print("EXIF LAT", lat)

        # lon = info.get("GPSLongitude")
        # if lon is not None:
        #     print("EXIF LON", lon)

        for name in removed:
            if name == "title":
                exif_args.append("-ImageDescription=")
            elif name == "author":
                exif_args.append("-Artist=")
            elif name == "image_orientation":
                exif_args.append("-Orientation=")
            elif name == "copyright":
                exif_args.append("-rights=")
                exif_args.append("-CopyrightNotice=")

        cmd = ["exiftool", "-c", "%f", "-overwrite_original", "-quiet", pathname] + exif_args
        res = subprocess.run(cmd)
        if res.returncode != 0:
            log.warn("%s: %s failed with code %d: %s",
                     pathname, " ".join(shlex.quote(x) for x in cmd), res.returncode)
            return False

        return True

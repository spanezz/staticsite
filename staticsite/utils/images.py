from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any
import PIL
import PIL.Image
import PIL.ExifTags
import subprocess
import json
import os
import logging

if TYPE_CHECKING:
    from staticsite.contents import ContentDir
    from staticsite import File
    from staticsite.cache import Cache
    from .typing import Meta

log = logging.getLogger("utils.images")

PIL_EXIF_TAGS = {v: k for k, v in PIL.ExifTags.TAGS.items()}
PIL_EXIF_GPSTAGS = {v: k for k, v in PIL.ExifTags.GPSTAGS.items()}

PIL_EXIF_GPSINFO = PIL_EXIF_TAGS["GPSInfo"]
PIL_EXIF_IMAGEDESCRIPTION = PIL_EXIF_TAGS["ImageDescription"]
PIL_EXIF_ORIENTATION = PIL_EXIF_TAGS["Orientation"]
PIL_EXIF_ARTIST = PIL_EXIF_TAGS["Artist"]


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

            getexif = getattr(img, "_getexif", None)
            if getexif is None:
                meta.update(self.read_meta_exiftool(pathname))
            else:
                exif = getexif()
                if exif is not None:
                    meta.update(self.read_meta_pil(exif))

        return meta

    def read_meta_pil(self, exif: Dict[int, Any]) -> Meta:
        # https://hhsprings.bitbucket.io/docs/programming/examples/python/PIL/ExifTags.html
        meta = {}

        # https://exiftool.org/TagNames/GPS.html
        gpsinfo = exif.get(PIL_EXIF_GPSINFO)
        if gpsinfo is not None:
            # https://gis.stackexchange.com/questions/136925/how-to-parse-exif-gps-information-to-lat-lng-decimal-numbers
            # https://stackoverflow.com/questions/2526304/php-extract-gps-exif-data

            latref = gpsinfo.get(PIL_EXIF_GPSTAGS["GPSLatitudeRef"], "N")
            lat = gpsinfo.get(PIL_EXIF_GPSTAGS["GPSLatitude"])
            if lat:
                meta["lat"] = parse_coord(latref, lat)

            lonref = gpsinfo.get(PIL_EXIF_GPSTAGS["GPSLongitudeRef"], "E")
            lon = gpsinfo.get(PIL_EXIF_GPSTAGS["GPSLongitude"])
            if lon:
                meta["lon"] = parse_coord(lonref, lon)

        description = exif.get(PIL_EXIF_IMAGEDESCRIPTION)
        if description is not None:
            meta["title"] = description

        artist = exif.get(PIL_EXIF_ARTIST)
        if artist is not None:
            meta["author"] = artist

        orientation = exif.get(PIL_EXIF_ORIENTATION)
        if orientation is not None:
            # https://www.impulseadventure.com/photo/exif-orientation.html
            meta["image_orientation"] = int(orientation)

        return meta

    def read_meta_exiftool(self, pathname: str) -> Meta:
        meta = {}

        # It is important to use abspath here, as exiftool does not support the
        # usual -- convention to deal with files starting with a dash. With abspath
        # at least the file name will start with a /
        res = subprocess.run(["exiftool", "-json", "-c", "%f", pathname], capture_output=True)
        if res.returncode != 0:
            log.warn("%s: exiftool failed with code %d: %s", pathname, res.returncode, res.stderr.strip())
            return meta

        info = json.loads(res.stdout)[0]

        description = info.get("Description")
        if description is not None:
            meta["title"] = description

        artist = info.get("Artist")
        if artist is not None:
            meta["author"] = artist

        orientation = info.get("Orientation")
        if orientation is not None:
            # https://www.impulseadventure.com/photo/exif-orientation.html
            meta["image_orientation"] = int(orientation)

        lat = info.get("GPSLatitude")
        if lat is not None:
            print("EXIF LAT", lat)

        lon = info.get("GPSLongitude")
        if lon is not None:
            print("EXIF LON", lon)

        # "DateTime": "2017:05:09 21:27:42",
        # "GPSLatitudeRef": "North",
        # "GPSAltitude": "92 m",
        # "GPSTimeStamp": "19:27:43",
        # "GPSDateStamp": "2017:05:09",
        # "GPSDateTime": "2017:05:09 19:27:43Z",
        # "GPSLatitude": "44 deg 59' 20.64\" N",
        # "GPSLongitude": "9 deg 50' 35.16\" E",
        # "GPSLongitudeRef": "East",
        # "GPSPosition": "44 deg 59' 20.64\" N, 9 deg 50' 35.16\" E",

        return meta

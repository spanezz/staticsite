# coding: utf-8
import os
import re
import datetime
import json
import logging
import pytz
from . import content

log = logging.getLogger()

tz_local = pytz.timezone("Europe/Rome")

class Page:
    def __init__(self, site, relpath):
        # Site that owns this page
        self.site = site

        # Relative path of the page in the source directory, as used to
        # reference the page in links
        self.src_relpath = relpath

        # Relative path of the page in the target directory, as used to
        # generate the output page
        self.dst_relpath = relpath

        # Relative link used to point to this resource in URLs
        self.dst_link = relpath

        # Page metadata. See README for a list.
        self.meta = {}

    @property
    def date_as_iso8601(self):
        from dateutil.tz import tzlocal
        ts = self.meta.get("date", None)
        if ts is None: return None
        # TODO: Take timezone from config instead of tzlocal()
        tz = tzlocal()
        ts = ts.astimezone(tz)
        offset = tz.utcoffset(ts)
        offset_sec = (offset.days * 24 * 3600 + offset.seconds)
        offset_hrs = offset_sec // 3600
        offset_min = offset_sec % 3600
        if offset:
            tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
        else:
            tz_str = 'Z'
        return ts.strftime("%Y-%m-%d %H:%M:%S") + tz_str

    def resolve_link(self, target):
        # Absolute URLs are resolved as is
        if target.startswith("/"):
            target_relpath = os.path.normpath(target.lstrip("/"))
            return self.site.pages.get(target_relpath, None)

        root = self.src_relpath
        while True:
            target_relpath = os.path.normpath(os.path.join(root, target))
            res = self.site.pages.get(target_relpath, None)
            if res is not None: return res
            if not root or root == "/":
                return None
            root = os.path.dirname(root)


    def read_metadata(self):
        """
        Fill in self.meta scanning the page contents
        """
        pass

    def transform(self):
        """
        Optionally transform the page, like remove it from the site, or
        generate variants.
        """
        pass


class Site:
    def __init__(self, root):
        self.root = root

        # Extra ctime information
        self.ctimes = None

        # Site pages
        self.pages = {}

        # Description of tags
        self.tag_descriptions = {}

        # Map input file patterns to resource handlers
        from .markdown import MarkdownPage
        from .j2 import J2Page
        self.page_handlers = [
            MarkdownPage,
            J2Page,
        ]

        self.taxonomies = {}
        self.taxonomy_indices = {}
        for n in ("tags", "stories"):
            self.taxonomies[n] = set()
            self.taxonomy_indices[n] = {}

    def read_tree(self, relpath=None):
        from .asset import Asset

        if relpath is None:
            log.info("Loading site directory %s", self.root)
            abspath = os.path.join(self.root)
        else:
            log.debug("Loading directory %s", relpath)
            abspath = os.path.join(self.root, relpath)
        for f in os.listdir(abspath):
            if f.startswith("."): continue

            if relpath is None:
                page_relpath = f
            else:
                page_relpath = os.path.join(relpath, f)

            absf = os.path.join(self.root, page_relpath)
            if os.path.isdir(absf):
                self.read_tree(page_relpath)
                continue

            for handler in self.page_handlers:
                p = handler.try_create(self, page_relpath)
                if p is not None:
                    self.pages[p.src_relpath] = p
                    break
            else:
                if os.path.isfile(absf):
                    log.debug("Loading static file %s", page_relpath)
                    p = Asset(self, page_relpath)
                    self.pages[p.src_relpath] = p

#    def read_tag_descriptions(self, relpath):
#        log.info("Loading tag info from %s", relpath)
#        abspath = os.path.join(self.root, relpath)
#        for f in os.listdir(abspath):
#            # Skip tag index
#            if f == "index.mdwn": continue
#            if not f.endswith(".mdwn"): continue
#            desc = []
#            tag = os.path.splitext(f)[0]
#            with open(os.path.join(abspath, f), "rt") as fd:
#                for line in fd:
#                    line = line.rstrip()
#                    if line.startswith("[[!"):
#                        if re.match(r'\[\[!inline pages="link\(tags/{tag}\)" show="\d+"\]\]'.format(tag=tag), line): continue
#                        log.warn("%s: found unsupported tag lookup: %s", os.path.join(relpath, f), line)
#                    else:
#                        desc.append(line)
#
#            # Strip leading and trailing empty lines
#            while desc and not desc[0]:
#                desc.pop(0)
#            while desc and not desc[-1]:
#                desc.pop(-1)
#            self.tag_descriptions[tag] = desc

    def relocate(self, page, dest_relpath):
        log.info("Relocating %s to %s", page.relpath, dest_relpath)
        if dest_relpath in self.pages:
            log.warn("Cannot relocate %s to existing page %s", page.relpath, dest_relpath)
            return
        self.pages[dest_relpath] = page
        page.aliases.append(page.relpath)
        page.relpath = dest_relpath

    def analyze(self):
        # First pass: read metadata
        for page in self.pages.values():
            page.read_metadata()

        # Second pass: aggregate metadata
        for page in self.pages.values():
            for name, vals in self.taxonomies.items():
                page_vals = page.meta.get(name, None)
                if page_vals is None: continue
                vals.update(page_vals)

        # Third pass: site transformations

        # Use a list because the dictionary can be modified by analyze()
        # methods
        for page in list(self.pages.values()):
            page.transform()

    def slugify(self, text):
        from .slugify import slugify
        return slugify(text)

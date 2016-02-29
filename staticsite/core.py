# coding: utf-8
import os
import re
import datetime
import json
import sys
import logging
import pytz
import fnmatch
from collections import defaultdict
import jinja2
from . import content

log = logging.getLogger()

class Settings:
    def __init__(self):
        from . import global_settings
        self.add_module(global_settings)

    def add_module(self, mod):
        """
        Add uppercase settings from mod into this module
        """
        for setting in dir(mod):
            if setting.isupper():
                setattr(self, setting, getattr(mod, setting))

settings = Settings()

def load_settings(pathname):
    orig_dwb = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        # http://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path

        # Seriously, this should not happen in the standard library. You do not
        # break stable APIs. You can extend them but not break them. And
        # especially, you do not break stable APIs and then complain that people
        # stick to 2.7 until its death, and probably after.
        if sys.version_info >= (3, 5):
            import importlib.util
            spec = importlib.util.spec_from_file_location("staticsite.settings", pathname)
            user_settings = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_settings)
        else:
            from importlib.machinery import SourceFileLoader
            user_settings = SourceFileLoader("staticsite.settings", pathname).load_module()
    finally:
        sys.dont_write_bytecode = orig_dwb

    settings.add_module(user_settings)


class Page:
    # In what pass must pages of this type be analyzed.
    ANALYZE_PASS = 1

    # True if the page can be found when search site contents
    FINDABLE = False

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
        self.dst_link = os.path.join(settings.SITE_ROOT, relpath)

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

    def check(self, checker):
        pass

    def target_relpaths(self):
        return [self.dst_relpath]


class Site:
    def __init__(self, root):
        self.root = root

        # Root of site pages
        self.site_root = os.path.join(root, "site")

        # Root of theme resources
        self.theme_root = os.path.join(root, "theme")

        # Extra ctime information
        self.ctimes = None

        # Site pages
        self.pages = {}

        # Description of tags
        self.tag_descriptions = {}

        # Site time zone
        self.timezone = pytz.timezone(settings.TIMEZONE)

        # Current datetime
        self.generation_time = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(self.timezone)

        # Jinja2 template engine
        from jinja2 import Environment, FileSystemLoader
        self.jinja2 = Environment(
            loader=FileSystemLoader([
                os.path.join(os.path.join(self.root, "site")),
                os.path.join(os.path.join(self.root, "theme")),
            ]),
            autoescape=True,
        )

        # Add settings to jinja2 globals
        for x in dir(settings):
            if not x.isupper(): continue
            self.jinja2.globals[x] = getattr(settings, x)


        # Install site's functions into the jinja2 environment
        self.jinja2.globals.update(
            url_for=self.jinja2_url_for,
            site_pages=self.jinja2_site_pages,
            now=self.generation_time,
        )
        self.jinja2.filters["datetime_format"] = self.jinja2_datetime_format

        # Map input file patterns to resource handlers
        from .markdown import MarkdownPages
        from .j2 import J2Pages
        from .taxonomy import TaxonomyPages
        self.page_handlers = [
            MarkdownPages(self.jinja2),
            J2Pages(self.jinja2),
            TaxonomyPages(self.jinja2),
        ]

    @jinja2.contextfilter
    def jinja2_datetime_format(self, context, dt, format=None):
        if format in ("rss2", "rfc822"):
            from email.utils import formatdate
            return formatdate(dt.timestamp())
        elif format in ("atom", "rfc3339"):
            dt = dt.astimezone(pytz.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif format == "w3cdtf":
            from dateutil.tz import tzlocal
            offset = dt.utcoffset()
            offset_sec = (offset.days * 24 * 3600 + offset.seconds)
            offset_hrs = offset_sec // 3600
            offset_min = offset_sec % 3600
            if offset:
                tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
            else:
                tz_str = 'Z'
            return dt.strftime("%Y-%m-%dT%H:%M:%S") + tz_str
        elif format == "iso8601" or format is None:
            from dateutil.tz import tzlocal
            offset = dt.utcoffset()
            offset_sec = (offset.days * 24 * 3600 + offset.seconds)
            offset_hrs = offset_sec // 3600
            offset_min = offset_sec % 3600
            if offset:
                tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
            else:
                tz_str = 'Z'
            return dt.strftime("%Y-%m-%d %H:%M:%S") + tz_str
        else:
            log.warn("%s+%s: invalid datetime format %r requested", cur_page.src_relpath, context.name, format)
            return "(unknown datetime format {})".format(format)


    @jinja2.contextfunction
    def jinja2_url_for(self, context, arg):
        if isinstance(arg, str):
            cur_page = context.parent["page"]
            page = cur_page.resolve_link(arg)
            if page is None:
                log.warn("%s+%s: unresolved link %s passed to url_for", cur_page.src_relpath, context.name, arg)
                return ""
        else:
            page = arg
        return page.dst_link

    @jinja2.contextfunction
    def jinja2_site_pages(self, context, path=None, limit=None, sort="-date"):
        if path is not None:
            re_path = re.compile(fnmatch.translate(path))
        else:
            re_path = None

        if sort is not None:
            if sort.startswith("-"):
                sort = sort[1:]
                sort_reverse = True
            else:
                sort_reverse = False

        pages = []
        for page in self.pages.values():
            if not page.FINDABLE: continue
            if re_path is not None and not re_path.match(page.src_relpath): continue
            if sort is not None and sort not in page.meta: continue
            pages.append(page)

        if sort is not None:
            pages.sort(key=lambda p: p.meta.get(sort, None), reverse=sort_reverse)

        if limit is not None:
            pages = pages[:limit]

        return pages

    def read_tree(self, relpath=None):
        from .asset import Asset

        if relpath is None:
            log.info("Loading site directory %s", self.site_root)
            abspath = self.site_root
        else:
            log.debug("Loading directory %s", relpath)
            abspath = os.path.join(self.site_root, relpath)
        for f in os.listdir(abspath):
            if f.startswith("."): continue

            if relpath is None:
                page_relpath = f
            else:
                page_relpath = os.path.join(relpath, f)

            absf = os.path.join(abspath, f)
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

    def read_theme_asset_tree(self, theme_assets_relpath, relpath=None):
        """
        Read static assets from a directory tree.

        theme_assets_relpath is the relative path of the root of the assets
        tree, rooted on the whole staticsite project (where settings.py is)
        """
        from .asset import ThemeAsset

        if relpath is None:
            log.info("Loading theme static asset directory %s", theme_assets_relpath)
            abspath = os.path.join(self.root, theme_assets_relpath)
        else:
            log.debug("Loading theme static asset directory %s/%s", theme_assets_relpath, relpath)
            abspath = os.path.join(self.root, theme_assets_relpath, relpath)

        for f in os.listdir(abspath):
            if f.startswith("."): continue

            if relpath is None:
                page_relpath = f
            else:
                page_relpath = os.path.join(relpath, f)

            absf = os.path.join(abspath, f)
            if os.path.isdir(absf):
                self.read_theme_asset_tree(theme_assets_relpath, page_relpath)
                continue

            if os.path.isfile(absf):
                log.debug("Loading theme static asset file %s/%s", theme_assets_relpath, page_relpath)
                p = ThemeAsset(self, page_relpath, theme_assets_relpath)
                self.pages[p.src_relpath] = p


    def relocate(self, page, dest_relpath):
        log.info("Relocating %s to %s", page.relpath, dest_relpath)
        if dest_relpath in self.pages:
            log.warn("Cannot relocate %s to existing page %s", page.relpath, dest_relpath)
            return
        self.pages[dest_relpath] = page
        page.aliases.append(page.relpath)
        page.relpath = dest_relpath

    def analyze(self):
        # Group pages by pass number
        by_pass = defaultdict(list)
        for page in self.pages.values():
            by_pass[page.ANALYZE_PASS].append(page)

        # Read metadata
        for passnum, pages in sorted(by_pass.items(), key=lambda x:x[0]):
            for page in pages:
                page.read_metadata()

    def slugify(self, text):
        from .slugify import slugify
        return slugify(text)

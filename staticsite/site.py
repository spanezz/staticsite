# coding: utf-8

import jinja2
import os
import re
import pytz
import datetime
import fnmatch
from collections import defaultdict
from .core import settings
import logging

log = logging.getLogger()

class Site:
    def __init__(self, root):
        self.root = root

        # Root of site pages
        self.site_root = os.path.join(root, "site")

        # Root of archetypes repository
        self.archetypes_root = os.path.join(root, "archetypes")

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
            from .utils import format_date_rfc822
            return format_date_rfc822(dt)
        elif format in ("atom", "rfc3339"):
            from .utils import format_date_rfc3339
            return format_date_rfc3339(dt)
        elif format == "w3cdtf":
            from .utils import format_date_w3cdtf
            return format_date_w3cdtf(dt)
        elif format == "iso8601" or not format:
            from .utils import format_date_iso8601
            return format_date_iso8601(dt)
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

    def read_site_tree(self, tree_root):
        """
        Read static assets and pages from a directory and all its subdirectories
        """
        from .asset import Asset

        log.info("Loading pages from %s", tree_root)

        for root, dnames, fnames in os.walk(tree_root):
            for f in fnames:
                if f.startswith("."): continue

                page_abspath = os.path.join(root, f)
                page_relpath = os.path.relpath(page_abspath, tree_root)

                for handler in self.page_handlers:
                    p = handler.try_load_page(self, tree_root, page_relpath)
                    if p is not None:
                        self.pages[p.link_relpath] = p
                        break
                else:
                    if os.path.isfile(page_abspath):
                        log.debug("Loading static file %s", page_relpath)
                        p = Asset(self, tree_root, page_relpath)
                        self.pages[p.link_relpath] = p

    def read_asset_tree(self, tree_root):
        """
        Read static assets from a directory and all its subdirectories
        """
        from .asset import Asset

        log.info("Loading assets from %s", tree_root)

        for root, dnames, fnames in os.walk(tree_root):
            for f in fnames:
                if f.startswith("."): continue

                page_abspath = os.path.join(root, f)
                if os.path.isfile(page_abspath):
                    page_relpath = os.path.relpath(page_abspath, tree_root)
                    log.debug("Loading static file %s", page_relpath)
                    p = Asset(self, tree_root, page_relpath)
                    self.pages[p.link_relpath] = p

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

    def load_archetype(self, name):
        """
        Read the archetypes directory and return the archetype that matches the given name.

        Returns None if nothing matches.
        """
        # Map input file patterns to resource handlers
        from .markdown import MarkdownPages
        handlers = [
            # Only resources that have a front matter can be used here, because
            # we need to read the front matter to determine the destination
            # path
            MarkdownPages(self.jinja2),
        ]

        for root, dnames, fnames in os.walk(self.archetypes_root):
            for f in fnames:
                if f.startswith("."): continue
                relpath = os.path.relpath(os.path.join(root, f), self.archetypes_root)
                for handler in handlers:
                    a = handler.try_load_archetype(self, relpath, name)
                    if a is not None:
                        return a
        return None

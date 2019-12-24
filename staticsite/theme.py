from __future__ import annotations
from typing import List, Optional, Union, Sequence
import jinja2
import os
import re
import datetime
import heapq
import logging
from .page import Page, PageNotFoundError
from .utils import front_matter
from .utils.typing import Meta
from .page_filter import PageFilter, sort_args
from .metadata import Metadata
from .file import File

log = logging.getLogger("theme")


class ThemeNotFoundError(Exception):
    pass


class Theme:
    def __init__(self, site, config: Meta):
        self.site = site
        self.config = config

        # Jinja2 Environment
        self.jinja2 = None

        # Cached list of metadata that are templates for other metadata
        self.metadata_templates: Optional[List[Metadata]] = None

        # Root directories of parent themes, in topological order
        self.parents = []

        # self.load_parents()

    @classmethod
    def create(cls, site, name: str, search_paths: Sequence[str] = None):
        """
        Create a Theme looking up its name in the theme search paths
        """
        if search_paths is None:
            search_paths = site.settings.THEME_PATHS

        for path in search_paths:
            root = os.path.join(path, name)
            if os.path.isdir(root):
                return cls(site, cls.load_config(root, name))

        raise ThemeNotFoundError(f"Theme {name!r} not found in {search_paths!r}")

    @classmethod
    def load_config(self, root: str, name: str):
        pathname = os.path.join(root, "config")
        if not os.path.isfile(pathname):
            config = {}
        else:
            with open(pathname, "rt") as fd:
                lines = [line.rstrip() for line in fd]
                fmt, config = front_matter.parse(lines)

        # Normalize 'extends' to a list of strings
        extends = config.get("extends")
        if extends is None:
            config["extends"] = []
        elif isinstance(extends, str):
            config["extends"] = [extends]

        # Theme name
        config["name"] = name

        # Absolute path to the root of the theme directory
        config["root"] = os.path.abspath(root)

        return config

    def load(self):
        # TODO: follow inheritance chain and build merged list of theme resources

        # Load feature plugins from the theme directory
        self.load_features()

        # We are done adding features
        self.site.features.commit()
        self.site.stage_features_constructed = True

        # Jinja2 template engine
        from jinja2 import FileSystemLoader
        if self.site.settings.JINJA2_SANDBOXED:
            from jinja2.sandbox import ImmutableSandboxedEnvironment
            env_cls = ImmutableSandboxedEnvironment
        else:
            from jinja2 import Environment
            env_cls = Environment

        self.jinja2 = env_cls(
            loader=FileSystemLoader([
                self.site.content_root,
                self.config["root"],
            ]),
            autoescape=True,
        )

        # Add settings to jinja2 globals
        for x in dir(self.site.settings):
            if not x.isupper():
                continue
            self.jinja2.globals[x] = getattr(self.site.settings, x)

        self.jinja2.globals["site"] = self.site
        self.jinja2.globals["regex"] = re.compile

        # Install site's functions into the jinja2 environment
        self.jinja2.globals.update(
            has_page=self.jinja2_has_page,
            url_for=self.jinja2_url_for,
            site_pages=self.jinja2_site_pages,
            now=self.site.generation_time,
            next_month=(
                self.site.generation_time.replace(day=1) + datetime.timedelta(days=40)).replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0),
        )

        self.jinja2.filters["datetime_format"] = self.jinja2_datetime_format
        self.jinja2.filters["basename"] = self.jinja2_basename
        self.jinja2.filters["arrange"] = self.jinja2_arrange

        # Add feature-provided globals and filters
        for feature in self.site.features.ordered():
            self.jinja2.globals.update(feature.j2_globals)
            self.jinja2.filters.update(feature.j2_filters)

    def load_features(self):
        """
        Load feature modules from the features/ theme directory
        """
        features_dir = os.path.join(self.config["root"], "features")
        if not os.path.isdir(features_dir):
            return
        self.site.features.load_feature_dir([features_dir])

    def scan_assets(self):
        """
        Load static assets
        """
        meta = dict(self.site.content_roots[0].meta)
        meta["asset"] = True
        meta["site_path"] = os.path.join(meta["site_path"], "static")

        theme_static = os.path.join(self.config["root"], "static")
        if os.path.isdir(theme_static):
            self.site.scan_tree(
                src=File("", os.path.abspath(theme_static), os.stat(theme_static)),
                meta=meta,
            )

        # Load system assets from site settings and theme configuration
        system_assets = set(self.site.settings.SYSTEM_ASSETS)
        system_assets.update(self.config.get("system_assets", ()))
        for name in system_assets:
            root = os.path.join("/usr/share/javascript", name)
            if not os.path.isdir(root):
                log.warning("%s: system asset directory not found", root)
                continue
            meta = dict(meta)
            meta["site_path"] = os.path.join("static", name)
            # TODO: make this a child of the previously scanned static
            self.site.scan_tree(
                src=File(name, root, os.stat(root)),
                meta=meta,
            )

    def precompile_metadata_templates(self, meta: Meta):
        """
        Precompile all the elements of the given metadata that are jinja2
        template strings
        """
        if self.metadata_templates is None:
            self.metadata_templates = [m for m in self.site.metadata.values() if m.template_for is not None]
        for metadata in self.metadata_templates:
            val = meta.get(metadata.name)
            if val is None:
                continue
            if isinstance(val, str):
                meta[metadata.name] = self.jinja2.from_string(val)

    def render_metadata_templates(self, page: Page):
        """
        Render all the elements of the given metadata that are jinja2
        template strings
        """
        if self.metadata_templates is None:
            self.metadata_templates = [m for m in self.site.metadata.values() if m.template_for is not None]

        for metadata in self.metadata_templates:
            src = page.meta.get(metadata.name)
            if src is None:
                continue
            if metadata.template_for in page.meta:
                continue
            if isinstance(src, str):
                src = self.jinja2.from_string(src)
                page.meta[metadata.name] = src
            page.meta[metadata.template_for] = jinja2.Markup(page.render_template(src))

    def jinja2_basename(self, val: str) -> str:
        return os.path.basename(val)

    @jinja2.contextfilter
    def jinja2_datetime_format(self, context, dt: datetime.datetime, format: str = None) -> str:
        if not isinstance(dt, datetime.datetime):
            import dateutil.parser
            dt = dateutil.parser.parse(dt)
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
        elif format[0] == '%':
            return dt.strftime(format)
        else:
            log.warn("%s+%s: invalid datetime format %r requested",
                     context.parent["page"].src.relpath, context.name, format)
            return "(unknown datetime format {})".format(format)

    def jinja2_arrange(self, pages: List[Page], sort: str, limit: Optional[int] = None) -> List[Page]:
        """
        Sort the pages by ``sort`` and take the first ``limit`` ones
        """
        sort_meta, reverse, key = sort_args(sort)
        if key is None:
            if limit is None:
                return pages
            else:
                return pages[:limit]
        else:
            if limit is None:
                return sorted(pages, key=key, reverse=reverse)
            elif limit == 1:
                if reverse:
                    return [max(pages, key=key)]
                else:
                    return [min(pages, key=key)]
            elif len(pages) > 10 and limit < len(pages) / 3:
                if reverse:
                    return heapq.nlargest(limit, pages, key=key)
                else:
                    return heapq.nsmallest(limit, pages, key=key)
            else:
                return sorted(pages, key=key, reverse=reverse)[:limit]

    @jinja2.contextfunction
    def jinja2_has_page(self, context, arg: str) -> bool:
        cur_page = context.parent["page"]
        try:
            cur_page.resolve_path(arg)
        except PageNotFoundError:
            return False
        else:
            return True

    @jinja2.contextfunction
    def jinja2_url_for(self, context, arg: Union[str, Page], absolute=False) -> str:
        """
        Generate a URL for a page, specified by path or with the page itself
        """
        cur_page = context.get("page")
        if cur_page is None:
            log.warn("%s+%s: url_for(%s): current page is not defined", cur_page, context.name, arg)
            return ""

        try:
            return cur_page.url_for(arg, absolute=absolute)
        except PageNotFoundError as e:
            log.warn("%s: %s", context.name, e)
            return ""

    @jinja2.contextfunction
    def jinja2_site_pages(
            self, context, path: str = None, limit: Optional[int] = None, sort: str = "-date", **kw) -> List[Page]:
        page_filter = PageFilter(self.site, path=path, limit=limit, sort=sort, **kw)
        return page_filter.filter(self.site.pages.values())

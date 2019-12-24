from __future__ import annotations
from typing import List, Optional, Union
import jinja2
import os
import re
import datetime
import heapq
import logging
from pathlib import Path
from .page import Page, PageNotFoundError
from .utils import front_matter
from .page_filter import PageFilter, sort_args
from .file import File

log = logging.getLogger("theme")


class Theme:
    def __init__(self, site, root):
        self.site = site

        # Absolute path to the root of the theme directory
        self.root = Path(os.path.abspath(root))

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
                self.root.as_posix(),
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

        # Load theme configuration if present
        config = self.root / "config"
        if config.is_file():
            with open(config, "rt") as fd:
                lines = [line.rstrip() for line in fd]
                fmt, self.config = front_matter.parse(lines)
        else:
            self.config = {}

    def load_features(self):
        """
        Load feature modules from the features/ theme directory
        """
        features_dir = self.root / "features"
        if not features_dir.is_dir():
            return
        self.site.features.load_feature_dir([features_dir.as_posix()])

    def scan_assets(self):
        """
        Load static assets
        """
        meta = dict(self.site.content_roots[0].meta)
        meta["asset"] = True
        meta["site_path"] = os.path.join(meta["site_path"], "static")

        theme_static = self.root / "static"
        if theme_static.is_dir():
            self.site.scan_tree(
                src=File("", theme_static.resolve().as_posix(), theme_static.stat()),
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

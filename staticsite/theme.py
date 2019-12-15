import jinja2
import os
import re
import datetime
import logging
from pathlib import Path
from .utils import parse_front_matter
from .page_filter import PageFilter

log = logging.getLogger()


class Theme:
    def __init__(self, site, root):
        self.site = site

        # Absolute path to the root of the theme directory
        self.root = Path(os.path.abspath(root))

        # Load feature plugins from the theme directory
        self.load_features()

        # We are done adding features
        self.site.features.commit()

        # Jinja2 template engine
        from jinja2 import Environment, FileSystemLoader
        self.jinja2 = Environment(
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

        # Add feature-provided globals and filters
        for feature in self.site.features.ordered():
            self.jinja2.globals.update(feature.j2_globals)
            self.jinja2.filters.update(feature.j2_filters)

        self.dir_template = self.jinja2.get_template("dir.html")

        # Load theme configuration if present
        config = self.root / "config"
        if config.is_file():
            with open(config, "rt") as fd:
                lines = [line.rstrip() for line in fd]
                fmt, self.config = parse_front_matter(lines)
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

    def load_assets(self):
        """
        Load static assets
        """
        theme_static = self.root / "static"
        if theme_static.is_dir():
            self.site.read_asset_tree(theme_static)

        # Load system assets from site settings and theme configuration
        system_assets = set(self.site.settings.SYSTEM_ASSETS)
        system_assets.update(self.config.get("system_assets", ()))
        for name in system_assets:
            root = os.path.join("/usr/share/javascript", name)
            if not os.path.isdir(root):
                log.warning("%s: system asset directory not found", root)
                continue
            self.site.read_asset_tree("/usr/share/javascript", name)

    def jinja2_basename(self, val):
        return os.path.basename(val)

    @jinja2.contextfilter
    def jinja2_datetime_format(self, context, dt, format=None):
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

    @jinja2.contextfunction
    def jinja2_has_page(self, context, arg):
        cur_page = context.parent["page"]
        page = cur_page.resolve_link(arg)
        return page is not None

    @jinja2.contextfunction
    def jinja2_url_for(self, context, arg):
        if isinstance(arg, str):
            cur_page = context.parent["page"]
            page = cur_page.resolve_link(arg)
            if page is None:
                log.warn("%s+%s: unresolved link %s passed to url_for", cur_page.src.relpath, context.name, arg)
                return ""
        else:
            page = arg
        return page.dst_link

    @jinja2.contextfunction
    def jinja2_site_pages(self, context, path=None, limit=None, sort="-date", **kw):
        page_filter = PageFilter(self.site, path=path, limit=limit, sort=sort, **kw)
        return page_filter.filter(self.site.pages.values())

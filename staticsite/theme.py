import jinja2
import os
import re
import fnmatch
import datetime
import logging

log = logging.getLogger()


class PageFilter:
    def __init__(self, site, path=None, limit=None, sort=None, **kw):
        self.site = site

        if path is not None:
            self.re_path = re.compile(fnmatch.translate(path))
        else:
            self.re_path = None

        self.sort = sort
        if sort is not None:
            if sort.startswith("-"):
                self.sort = sort[1:]
                self.sort_reverse = True
            else:
                self.sort_reverse = False

        self.taxonomy_filters = []
        for taxonomy in self.site.taxonomies:
            t_filter = kw.get(taxonomy.name)
            if t_filter is None:
                continue
            self.taxonomy_filters.append((taxonomy.name, frozenset(t_filter)))

        self.limit = limit

    def filter(self, all_pages):
        pages = []

        for page in all_pages:
            if not page.FINDABLE:
                continue
            if self.re_path is not None and not self.re_path.match(page.src_relpath):
                continue
            if self.sort is not None and self.sort != "url" and self.sort not in page.meta:
                continue
            fail_taxonomies = False
            for name, t_filter in self.taxonomy_filters:
                page_tags = frozenset(page.meta.get(name, ()))
                if not t_filter.issubset(page_tags):
                    fail_taxonomies = True
            if fail_taxonomies:
                    continue
            pages.append(page)

        if self.sort is not None:
            if self.sort == "url":
                def sort_by(p):
                    return p.dst_link
            else:
                def sort_by(p):
                    return p.meta.get(self.sort, None)
            pages.sort(key=sort_by, reverse=self.sort_reverse)

        if self.limit is not None:
            pages = pages[:self.limit]

        return pages


class Theme:
    def __init__(self, site, root):
        self.site = site

        # Absolute path to the root of the theme directory
        self.root = os.path.abspath(root)

        # Jinja2 template engine
        from jinja2 import Environment, FileSystemLoader
        self.jinja2 = Environment(
            loader=FileSystemLoader([
                self.root,
            ]),
            autoescape=True,
        )

        # Add settings to jinja2 globals
        for x in dir(self.site.settings):
            if not x.isupper():
                continue
            self.jinja2.globals[x] = getattr(self.site.settings, x)

        # Install site's functions into the jinja2 environment
        self.jinja2.globals.update(
            has_page=self.jinja2_has_page,
            url_for=self.jinja2_url_for,
            site_pages=self.jinja2_site_pages,
            site_data_pages=self.jinja2_site_data_pages,
            now=self.site.generation_time,
            next_month=(
                self.site.generation_time.replace(day=1) + datetime.timedelta(days=40)).replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0),
            taxonomies=self.jinja2_taxonomies,
        )
        self.jinja2.filters["datetime_format"] = self.jinja2_datetime_format
        self.jinja2.filters["markdown"] = self.jinja2_markdown
        self.jinja2.filters["basename"] = self.jinja2_basename

        self.dir_template = self.jinja2.get_template("dir.html")

        self.load_plugins()

    def load_plugins(self):
        """
        Load plugin files from the plugins/ theme directory
        """
        plugin_dir = os.path.join(self.root, "plugins")
        if not os.path.isdir(plugin_dir):
            return

        for fn in os.listdir(plugin_dir):
            if not fn.endswith(".py"):
                continue
            self.load_plugin(os.path.join(plugin_dir, fn))

    def load_plugin(self, fname):
        """
        Load plugin code from the given file
        """
        with open(fname) as fd:
            try:
                code = compile(fd.read(), fname, 'exec')
            except Exception:
                log.exception("%s: plugin file failed to compile", fname)
                return

        plugin_env = {}
        try:
            exec(code, plugin_env)
        except Exception:
            log.exception("%s: plugin file failed to execute", fname)
            return

        plugin_load = plugin_env.get("load")
        if plugin_load is None:
            log.warn("%s: plugin did not define a load function", fname)
            return

        try:
            plugin_load(self)
        except Exception:
            log.exception("%s: plugin load function failed", fname)

    def jinja2_taxonomies(self):
        return self.site.taxonomies

    def jinja2_basename(self, val):
        return os.path.basename(val)

    @jinja2.contextfilter
    def jinja2_markdown(self, context, mdtext):
        return jinja2.Markup(self.site.markdown_renderer.render(context.parent["page"], mdtext))

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
                     context.parent["page"].src_relpath, context.name, format)
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
                log.warn("%s+%s: unresolved link %s passed to url_for", cur_page.src_relpath, context.name, arg)
                return ""
        else:
            page = arg
        return page.dst_link

    @jinja2.contextfunction
    def jinja2_site_pages(self, context, path=None, limit=None, sort="-date", **kw):
        page_filter = PageFilter(self.site, path=path, limit=limit, sort=sort, **kw)
        return page_filter.filter(self.site.pages.values())

    @jinja2.contextfunction
    def jinja2_site_data_pages(self, context, type, path=None, limit=None, sort=None, **kw):
        page_filter = PageFilter(self.site, path=path, limit=limit, sort=sort, **kw)
        return page_filter.filter(self.site.data_pages.by_type.get(type, []))

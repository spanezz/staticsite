# coding: utf-8
import jinja2
import os
import re
import fnmatch
import datetime
import logging

log = logging.getLogger()

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
            if not x.isupper(): continue
            self.jinja2.globals[x] = getattr(self.site.settings, x)

        # Install site's functions into the jinja2 environment
        self.jinja2.globals.update(
            has_page=self.jinja2_has_page,
            url_for=self.jinja2_url_for,
            site_pages=self.jinja2_site_pages,
            now=self.site.generation_time,
            next_month=(self.site.generation_time.replace(day=1) + datetime.timedelta(days=40)).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            taxonomies=self.jinja2_taxonomies,
        )
        self.jinja2.filters["datetime_format"] = self.jinja2_datetime_format
        self.jinja2.filters["markdown"] = self.jinja2_markdown
        self.jinja2.filters["basename"] = self.jinja2_basename

        self.dir_template = self.jinja2.get_template("dir.html")

    def jinja2_taxonomies(self):
        return self.site.taxonomies

    def jinja2_basename(self, val):
        return os.path.basename(val)

    @jinja2.contextfilter
    def jinja2_markdown(self, context, mdtext):
        return jinja2.Markup(self.site.markdown_renderer.render(context.parent["page"], mdtext))

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
        for page in self.site.pages.values():
            if not page.FINDABLE: continue
            if re_path is not None and not re_path.match(page.src_relpath): continue
            if sort is not None and sort not in page.meta: continue
            pages.append(page)

        if sort is not None:
            pages.sort(key=lambda p: p.meta.get(sort, None), reverse=sort_reverse)

        if limit is not None:
            pages = pages[:limit]

        return pages


from __future__ import annotations
from typing import Dict, Any
import os
import logging
import datetime
from urllib.parse import urlparse, urlunparse
from .utils import lazy
from .render import RenderedString
import jinja2
import dateutil.parser
import staticsite

log = logging.getLogger("page")


class Page:
    """
    A source page in the site.

    This can be a static asset, a file to be rendered, a taxonomy, a
    directory listing, or anything else.

    All pages have a number of members to describe their behaviour in the site:

    `site`:
        the Site that contains the page
    `src`:
        the File object with informationm about the source file
    `src_linkpath`:
        the path used by other pages to link to this page, when referencing its
        source. For example, blog/2016/example.md is linked as
        blog/2016/example.
    `dst_relpath`:
        relative path of the file that will be generated for this page when it
        gets rendered.
        FIXME: now that a resource can generate multiple files, this is not
        really needed.
    `dst_link`:
        absolute path in the site namespace used to link to this page in
        webpages.
        FIXME: now that a resource can generate multiple files, this is not
        really needed.
    `meta`:
        a dictionary with the page metadata. See the README for documentation
        about its contents.
    """
    # Page type
    TYPE: str

    def __init__(
            self,
            site: "staticsite.Site",
            src: "staticsite.File",
            src_linkpath: str,
            dst_relpath: str,
            dst_link: str,
            meta: Dict[str, Any] = None):
        self.site = site
        self.src = src
        self.src_linkpath = src_linkpath
        self.dst_relpath = dst_relpath
        self.dst_link = dst_link
        self.meta: Dict[str, Any]
        if meta is None:
            self.meta = {}
        else:
            self.meta = dict(meta)
        log.debug("%s: new page, src_link: %s", self.src.relpath, src_linkpath)

    def is_valid(self) -> bool:
        """
        Enforce common meta invariants.

        Performs validation and completion of metadata.

        :return: True if the page is valid and ready to be added to the site,
                 False if it should be discarded
        """
        # indexed must exist and be a bool
        indexed = self.meta.get("indexed", False)
        if isinstance(indexed, str):
            indexed = indexed.lower() in ("yes", "true", "1")
        self.meta["indexed"] = indexed

        # date must exist, and be a datetime
        date = self.meta.get("date")
        if date is None:
            if self.src.stat is not None:
                self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)
            else:
                self.meta["date"] = self.site.generation_time
        elif not isinstance(date, datetime.datetime):
            self.meta["date"] = dateutil.parser.parse(date)

        # template must exist, and defaults to page.html
        self.meta.setdefault("template", "page.html")

        # date must be an aware datetime
        if self.meta["date"].tzinfo is None:
            if hasattr(self.site.timezone, "localize"):
                self.meta["date"] = self.site.timezone.localize(self.meta["date"])
            else:
                self.meta["date"] = self.meta["date"].replace(tzinfo=self.site.timezone)

        # title must exist
        title = self._fill_possibly_templatized_meta_value("title")
        if title is None:
            self.meta["title"] = os.path.basename(self.src_linkpath)

        # description may exist
        self._fill_possibly_templatized_meta_value("description")

        # Check draft status
        if self.site.settings.DRAFT_MODE:
            return True
        if self.draft:
            log.info("%s: still a draft", self.src.relpath)
            return False
        return True

    def _fill_possibly_templatized_meta_value(self, name):
        # If there is a value for the field, we're done
        val = self.meta.get(name)
        if val is not None:
            return val

        # If there's a templatized value for the field, render it
        template_val = self.meta.get(f"template_{name}")
        if template_val is not None:
            val = jinja2.Markup(self.render_template(
                    self.site.theme.jinja2.from_string(template_val)))
            self.meta[name] = val
            return val

        # Else we could not fill
        return None

    @property
    def draft(self):
        """
        Return True if this page is still a draft (i.e. its date is in the future)
        """
        ts = self.meta.get("date", None)
        if ts is None:
            return False
        if ts <= self.site.generation_time:
            return False
        return True

    @lazy
    def page_template(self):
        template = self.meta["template"]
        if isinstance(template, jinja2.Template):
            return template
        return self.site.theme.jinja2.get_template(template)

    @lazy
    def redirect_template(self):
        return self.site.theme.jinja2.get_template("redirect.html")

    @property
    def date_as_iso8601(self):
        from dateutil.tz import tzlocal
        ts = self.meta.get("date", None)
        if ts is None:
            return None
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
        dirname, basename = os.path.split(target)
        if basename == "index.html":
            # log.debug("%s: resolve %s using %s", self.src.relpath, target, dirname)
            target = dirname
        # else:
            # log.debug("%s: resolve %s using %s", self.src.relpath, target, target)

        # Absolute URLs are resolved as is
        if target.startswith("/"):
            if target == "/":
                target_relpath = ""
            else:
                target_relpath = os.path.normpath(target.lstrip("/"))
            # log.debug("%s: resolve absolute path using %s", self.src.relpath, target_relpath)
            return self.site.pages.get(target_relpath, None)

        root = os.path.dirname(self.src.relpath)
        while True:
            target_relpath = os.path.normpath(os.path.join(root, target))
            if target_relpath == ".":
                target_relpath = ""
            res = self.site.pages.get(target_relpath, None)
            if res is not None:
                return res
            if not root or root == "/":
                return None
            root = os.path.dirname(root)

    def resolve_url(self, url):
        """
        Resolve internal URLs.

        Returns None if the URL does not need changing, else returns the new URL.
        """
        from markdown.util import AMP_SUBSTITUTE
        if not url:
            return None
        if url.startswith(AMP_SUBSTITUTE):
            # Possibly an overencoded mailto: link.
            # see https://bugs.debian.org/816218
            #
            # Markdown then further escapes & with utils.AMP_SUBSTITUTE, so
            # we look for it here.
            return None
        parsed = urlparse(url)
        if parsed.scheme or parsed.netloc:
            return None
        if not parsed.path:
            return None
        dest = self.resolve_link(parsed.path)
        if dest is None:
            # If resolving the full path failed, try resolving without extension
            pos = parsed.path.rfind(".")
            if pos == -1:
                return None

            # Treat .md and .rst as strippable extensions
            # TODO: deprecate this functionality and always link to full source
            #       paths with extension instead
            # TODO: have features provide this list instead of hardcoding it
            ext = parsed.path[pos:]
            if ext not in (".md", ".rst"):
                return None

            dirname, basename = os.path.split(parsed.path)
            # TODO: also generate this list from features
            if basename in ("index.md", "README.md", "index.rst", "README.rst"):
                dest = self.resolve_link(dirname)
            else:
                dest = self.resolve_link(parsed.path[:-len(ext)])
        if dest is None:
            log.warn("%s: internal link %r does not resolve to any site page", self.src.relpath, url)
            return None

        return urlunparse(
            (parsed.scheme, parsed.netloc, dest.dst_link, parsed.params, parsed.query, parsed.fragment)
        )

    def check(self, checker):
        pass

    def target_relpaths(self):
        res = [self.dst_relpath]
        for relpath in self.meta.get("aliases", ()):
            res.append(os.path.join(relpath, "index.html"))
        return res

    def __str__(self):
        return self.src.relpath

    def __repr__(self):
        return "{}:{}".format(self.TYPE, self.src.relpath)

    def to_dict(self):
        from .utils import dump_meta
        res = {
            "src": {
                "relpath": str(self.src.relpath),
                "root": str(self.src.root),
                "abspath": str(self.src.abspath),
            },
            "src_linkpath": str(self.src_linkpath),
            "dst_relpath": str(self.dst_relpath),
            "dst_link": str(self.dst_link),
            "meta": dump_meta(self.meta),
        }
        return res

    def render(self):
        res = {
            self.dst_relpath: RenderedString(self.render_template(self.page_template)),
        }

        aliases = self.meta.get("aliases", ())
        if aliases:
            for relpath in aliases:
                html = self.render_template(self.redirect_template)
                res[os.path.join(relpath, "index.html")] = RenderedString(html)

        return res

    def render_template(self, template: jinja2.Template, template_args: Dict[Any, Any] = None) -> str:
        """
        Render a jinja2 template, logging things if something goes wrong
        """
        if template_args is None:
            template_args = {}
        template_args.setdefault("page", self)
        try:
            return template.render(**template_args)
        except jinja2.TemplateError as e:
            log.error("%s: failed to render %s: %s", template.filename, self.src.relpath, e)
            log.debug("%s: failed to render %s: %s", template.filename, self.src.relpath, e, exc_info=True)
            # TODO: return a "render error" page? But that risks silent errors
            return None

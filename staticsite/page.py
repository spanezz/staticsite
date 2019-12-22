from __future__ import annotations
from typing import Dict, Any
import os
import logging
import datetime
from urllib.parse import urlparse, urlunparse
from .utils import lazy
from .utils.typing import Meta
from .render import RenderedString
import jinja2
import dateutil.parser
import staticsite

log = logging.getLogger("page")


class PageNotFoundError(Exception):
    pass


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
    `site_relpath`:
        path in the site namespace used to link to this page in webpages. For
        example, `blog/2016/example.md` is linked as `blog/2016/example/` in
        the built website.
    `dst_relpath`:
        relative path in the build directory for the file that will be written
        when this page gets rendered. For example, `blog/2016/example.md`
        generates `blog/2016/example/index.html`.
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
            site_relpath: str,
            dst_relpath: str,
            meta: Meta):
        self.site = site
        self.src = src
        self.site_relpath = site_relpath
        self.dst_relpath = dst_relpath
        self.meta: Meta
        if meta is None:
            self.meta = {}
        else:
            self.meta = dict(meta)

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
            self.meta["title"] = self.meta["site_name"]

        # description may exist
        self._fill_possibly_templatized_meta_value("description")

        # Check draft status
        if self.site.settings.DRAFT_MODE:
            return True
        if self.draft:
            log.info("%s: still a draft", self.src.relpath)
            return False

        # Check the existance of other mandatory fields
        if "site_root" not in self.meta:
            log.warn("%s: missing meta.site_root", self)
            return False
        if "site_url" not in self.meta:
            log.warn("%s: missing meta.site_url", self)
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

    def resolve_path(self, target: str) -> "Page":
        """
        Return a Page from the site, given a source or site path relative to
        this page.

        The path is resolved relative to this page, and if not found, relative
        to the parent page, and so on until the top.
        """
        # Absolute URLs are resolved as is
        if target.startswith("/"):
            if target == "/":
                target_relpath = ""
            else:
                target_relpath = os.path.normpath(target.lstrip("/"))

            # Try by source path
            res = self.site.pages_by_src_relpath.get(target_relpath)
            if res is not None:
                return res

            # Try by site path
            res = self.site.pages.get(target_relpath)
            if res is not None:
                return res

            # Try adding /static as a compatibility with old links
            target_relpath = "static/" + target_relpath

            # Try by source path
            res = self.site.pages_by_src_relpath.get(target_relpath)
            if res is not None:
                log.warn("%s+%s: please use /static/%s instead of %s", self, target, target)
                return res

            raise PageNotFoundError(f"cannot resolve {target} relative to {self}")

        # Relative urls are tried based on all path components of this page,
        # from the bottom up

        # First using the source paths
        root = os.path.dirname(self.src.relpath)
        while True:
            target_relpath = os.path.normpath(os.path.join(root, target))
            if target_relpath == ".":
                target_relpath = ""

            res = self.site.pages_by_src_relpath.get(target_relpath)
            if res is not None:
                return res

            if not root:
                break

            root = os.path.dirname(root)

        # The using the site paths
        root = self.site_relpath
        while True:
            target_relpath = os.path.normpath(os.path.join(root, target))
            if target_relpath == ".":
                target_relpath = ""

            res = self.site.pages.get(target_relpath)
            if res is not None:
                return res

            # print("RES", res)
            if not root:
                break

            root = os.path.dirname(root)

        raise PageNotFoundError(f"cannot resolve `{target}` relative to `{self}`")

    def resolve_url(self, url: str) -> str:
        """
        Resolve internal URLs.

        Returns the argument itself if the URL does not need changing, else
        returns the new URL.

        To check for a noop, check like ``if page.resolve_url(url) is url``

        This is used by url resolver postprocessors, like in markdown or
        restructured text pages.

        For resolving urls in templates, see Theme.jinja2_url_for().
        """
        parsed = urlparse(url)
        if parsed.scheme or parsed.netloc:
            return url
        if not parsed.path:
            return url

        try:
            dest: "Page" = self.resolve_path(parsed.path)
        except PageNotFoundError as e:
            log.warn("%s", e)
            return url

        return urlunparse(
            (parsed.scheme, parsed.netloc,
             os.path.join(dest.meta["site_root"], dest.site_relpath),
             parsed.params, parsed.query, parsed.fragment)
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
            "site_relpath": str(self.site_relpath),
            "dst_relpath": str(self.dst_relpath),
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

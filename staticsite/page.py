from __future__ import annotations

import logging
import os
from functools import cached_property
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, Type
from urllib.parse import urlparse, urlunparse

import jinja2
import markupsafe

from . import fields
from .site import SiteElement
from .node import Path
from .render import RenderedString

if TYPE_CHECKING:
    from .file import File
    from .node import Node
    from .render import RenderedElement
    from .site import Site

log = logging.getLogger("page")


class PageNotFoundError(Exception):
    pass


class PageValidationError(Exception):
    def __init__(self, page: "Page", msg: str):
        self.page = page
        self.msg = msg


class PageMissesFieldError(PageValidationError):
    def __init__(self, page: "Page", field: str):
        super().__init__(page, f"missing required field meta.{field}")


class TemplateField(fields.Field):
    """
    Template name or compiled template, taking its default value from Page.TEMPLATE
    """
    def __get__(self, page: Page, type: Type = None) -> Any:
        if self.name not in page.__dict__:
            if (val := getattr(page, "TEMPLATE", None)):
                page.__dict__[self.name] = val
                return val
            else:
                return self.default
        else:
            return page.__dict__[self.name]


class PageDate(fields.Date):
    """
    Make sure, on page load, that the element is a valid aware datetime object
    """
    def __get__(self, page: Page, type: Type = None) -> Any:
        if (date := page.__dict__.get(self.name)) is None:
            if (src := page.src) is not None and src.stat is not None:
                date = page.site.localized_timestamp(src.stat.st_mtime)
            else:
                date = page.site.generation_time
            page.__dict__[self.name] = date
        return date


class Draft(fields.Bool):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def __get__(self, page: Page, type: Type = None) -> Any:
        if (value := page.__dict__.get(self.name)) is None:
            value = page.date > page.site.generation_time
            page.__dict__[self.name] = value
            return value
        else:
            return value


class RenderedField(fields.Field):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def __get__(self, page: Page, type: Type = None) -> Any:
        if (value := page.__dict__.get(self.name)) is None:
            if (tpl := getattr(page, "template_" + self.name, None)):
                # If a template exists, render it
                # TODO: remove meta= and make it compatibile again with stable staticsite
                value = markupsafe.Markup(tpl.render(meta=page.meta, page=page))
            else:
                value = self.default
            self.__dict__[self.name] = value
        return value


class RenderedTitleField(fields.Field):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def __get__(self, page: Page, type: Type = None) -> Any:
        if (value := page.__dict__.get(self.name)) is None:
            if (tpl := getattr(page, "template_" + self.name, None)):
                # If a template exists, render it
                # TODO: remove meta= and make it compatibile again with stable staticsite
                value = markupsafe.Markup(tpl.render(meta=page.meta, page=page))
            else:
                value = page.site_name
            self.__dict__[self.name] = value
        return value


class Related:
    """
    Container for related pages
    """
    def __init__(self, page: Page):
        self.page = page
        self.pages: dict[str, Union[str, Page]] = {}

    def __repr__(self):
        return f"Related({self.page!r}, {self.pages!r}))"

    def __str__(self):
        return self.pages.__str__()

    def __getitem__(self, name: str):
        if (val := self.pages.get(name)) is None:
            pass
        elif isinstance(val, str):
            val = self.page.resolve_path(val)
            self.pages[name] = val
        return val

    def __setitem__(self, name: str, page: Union[str, Page]):
        if (old := self.pages.get(name)) is not None and old != self.page:
            log.warn("%s: attempt to set related.%s to %r but it was already %r",
                     self, name, page, old)
            return
        self.pages[name] = page

    def to_dict(self):
        return self.pages

    def get(self, *args):
        return self.pages.get(*args)

    def keys(self):
        return self.pages.keys()

    def values(self):
        return self.pages.values()

    def items(self):
        return self.pages.items()

    def __eq__(self, obj: Any) -> bool:
        if isinstance(obj, Related):
            return self.page == obj.page and self.pages == obj.pages
        elif isinstance(obj, dict):
            return self.pages == obj
        elif obj is None:
            return False
        else:
            return False


class RelatedField(fields.Field):
    """
    Contains related pages indexed by name
    """
    def __get__(self, page: Page, type: Type = None) -> Any:
        if (value := page.__dict__.get(self.name)) is None:
            value = Related(page)
            page.__dict__[self.name] = value
        return value

    def __set__(self, page: Page, value: Any) -> None:
        related = self.__get__(page)
        related.pages.update(value)


class Meta:
    """
    Read-only dict accessor to Page's fields
    """
    def __init__(self, page: Page):
        self._page = page

    def __getitem__(self, key: str) -> Any:
        if key not in self._page._fields:
            raise KeyError(key)

        try:
            res = getattr(self._page, key)
            # print(f"{self._page!r} meta[{key!r}] = {res!r}")
            return res
        except AttributeError:
            raise KeyError(key)

    def __contains__(self, key: str):
        if key not in self._page._fields:
            return False

        return getattr(self._page, key) is not None

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self._page._fields:
            return default

        return getattr(self._page, key, default)

    def to_dict(self) -> dict[str, Any]:
        """
        Return a dict with all the values of this Meta, including the inherited
        ones
        """
        res = {}
        for key in self._page._fields:
            if (val := getattr(self._page, key)) is not None:
                res[key] = val
        return res


class Page(SiteElement):
    """
    A source page in the site.

    This can be a static asset, a file to be rendered, a taxonomy, a
    directory listing, or anything else.
    """
    # Page type
    TYPE: str
    # Default page template
    TEMPLATE = "page.html"

    created_from = fields.Field(doc="""
        Page that generated this page.

        This is only set in autogenerated pages.
    """)

    date = PageDate(doc="""
        Publication date for the page.

        A python datetime object, timezone aware. If the date is in the future when
        `ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
        --draft` to also consider draft pages.

        If missing, the modification time of the file is used.
    """)

    template = TemplateField(doc="""
        Template used to render the page. Defaults to `page.html`, although specific
        pages of some features can default to other template names.

        Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).
    """)

    copyright = RenderedField(doc="""
        Copyright notice for the page. If missing, it's generated using
        `template_copyright`.
    """)

    title = RenderedTitleField(doc="""
        Page title.

        If missing:

         * it is generated via template_title, if present
         * the first title found in the page contents is used.
         * in the case of jinaj2 template pages, the contents of `{% block title %}`,
           if present, is rendered and used.
         * if the page has no title, the title of directory indices above this page is
           inherited.
         * if still no title can be found, the site name is used as a default.
    """)

    description = RenderedField(doc="""
        The page description. If omitted, the page will have no description.
    """)

    draft = Draft(doc="""
If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.

It defaults to false, or true if `meta.date` is in the future.
""")

    indexed = fields.Bool(default=False, doc="""
        If true, the page appears in [directory indices](dir.md) and in
        [page filter results](page_filter.md).

        It defaults to true at least for [Markdown](markdown.md),
        [reStructuredText](rst.rst), and [data](data.md) pages.
    """)

    related = RelatedField(structure=True, doc="""
        Dict of pages related to this page.

        Dict values will be resolved as pages.

        If there are no related pages, `page.meta.related` will be guaranteed to exist
        as an empty dictionary.

        Features can add to this. For example, [syndication](syndication.md) can add
        `meta.related.archive`, `meta.related.rss`, and `meta.related.atom`.
    """)

    def __init__(
            self, site: Site, *,
            node: Node,
            created_from: Optional[Page] = None,
            search_root_node: Node,
            src: Optional[File] = None,
            dst: str,
            leaf: bool,
            directory_index: bool = False,
            **kw):
        # Set these fields early as they are used by __str__/__repr__
        # Node where this page is installed in the rendered structure
        self.node: Node = node
        # File object for this page on disk, or None if this is an autogenerated page
        self.src = src

        super().__init__(site, parent=created_from or node, **kw)

        # Read-only, dict-like accessor to the page's fields
        self.meta: Meta = Meta(self)
        # Node to use as initial node for find_pages
        self.search_root_node: Node = search_root_node
        # Name of the file used to render this page on build
        self.dst: str = dst
        if created_from:
            self.created_from = created_from
        # Set to True if this page is a directory index. This affects the root
        # of page lookups relative to this page
        self.directory_index: bool = directory_index
        # Set to True if this page is shown as a file url, False if it's shown
        # as a path url
        self.leaf: bool = leaf

        # True if this page can render a short version of itself
        self.content_has_split = False

        # External links found when rendering the page
        self.rendered_external_links: set[str] = set()

        # Check the existence of other mandatory fields
        if self.site_url is None:
            raise PageMissesFieldError(self, "site_url")

    @property
    def site_path(self) -> str:
        """
        Accessor to support the migration away from meta['build_path']
        """
        # return self.meta["build_path"]
        if self.leaf:
            return os.path.join(self.node.compute_path(), self.dst)
        else:
            return self.node.compute_path()

    @property
    def build_path(self) -> str:
        """
        Accessor to support the migration away from meta['build_path']
        """
        return os.path.join(self.node.compute_path(), self.dst)

    def add_related(self, name: str, page: "Page"):
        """
        Set the page as meta.related.name
        """
        self.related[name] = page

    @cached_property
    def page_template(self):
        template = self.meta["template"]
        if isinstance(template, jinja2.Template):
            return template
        return self.site.theme.jinja2.get_template(template)

    @property
    def date_as_iso8601(self):
        from dateutil.tz import tzlocal
        if (ts := self.date) is None:
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

    def find_pages(
            self,
            path: Optional[str] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None,
            root: Optional[str] = None,
            **kw) -> List["Page"]:
        """
        If not set, default root to the path of the containing directory for
        this page
        """
        if root is None:
            root = self.search_root_node

        # print(f"find_pages {root=}, {path=!r}")

        from .page_filter import PageFilter
        f = PageFilter(self.site, path, limit, sort, root=root, **kw)
        return f.filter()

    def resolve_path(self, target: Union[str, "Page"], static=False) -> "Page":
        """
        Return a Page from the site, given a source or site path relative to
        this page.

        The path is resolved relative to this page, and if not found, relative
        to the parent page, and so on until the top.
        """
        if isinstance(target, Page):
            return target

        # print(f"Page.resolve_path {self=!r}, {target=!r}")
        # Find the start node for the search
        if target.startswith("/"):
            root = self.site.root
            if static:
                root = root.lookup(Path.from_string(self.site.settings.STATIC_PATH))
        else:
            root = self.search_root_node
        path = Path.from_string(target)
        # print(f"Page.resolve_path  start from {root.compute_path()!r}, path={path!r}")

        dst = root.lookup_page(path)
        # print(f"Page.resolve_path  found {dst=!r}")
        if dst is None:
            raise PageNotFoundError(f"cannot resolve {target!r} relative to {self!r}")
        else:
            return dst

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
            dest = self.url_for(parsed.path)
        except PageNotFoundError as e:
            log.warn("%s: %s", self, e)
            return url

        dest = urlparse(dest)

        return urlunparse(
            (dest.scheme, dest.netloc, dest.path,
             parsed.params, parsed.query, parsed.fragment)
        )

    def url_for(self, target: Union[str, "Page"], absolute=False, static=False) -> str:
        """
        Generate a URL for a page, specified by path or with the page itself
        """
        # print(f"Page.url_for {self=!r}, {target=!r}")
        page: "Page"

        if isinstance(target, str):
            page = self.resolve_path(target, static=static)
        else:
            page = target

        # print(f"Page.url_for {self=!r}, {target=!r}, {page=!r}")

        # If the destination has a different site_url, generate an absolute url
        if self.site_url != page.site_url:
            absolute = True

        if absolute:
            site_url = page.site_url.rstrip("/")
            return f"{site_url}/{page.site_path}"
        else:
            return "/" + page.site_path

    def get_img_attributes(
            self, image: Union[str, "Page"], type: Optional[str] = None, absolute=False) -> Dict[str, str]:
        """
        Given a path to an image page, return a dict with <img> attributes that
        can be used to refer to it
        """
        img = self.resolve_path(image)

        res = {
            "alt": img.title,
        }

        if type is not None:
            # If a specific version is required, do not use srcset
            rel = img.related.get(type, img)
            res["width"] = str(rel.width)
            res["height"] = str(rel.height)
            res["src"] = self.url_for(rel, absolute=absolute)
        else:
            # https://developers.google.com/web/ilt/pwa/lab-responsive-images
            # https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Responsive_images
            srcsets = []
            for rel in img.related.values():
                if rel.TYPE != "image":
                    continue

                if (width := rel.width) is None:
                    continue

                url = self.url_for(rel, absolute=absolute)
                srcsets.append(f"{markupsafe.escape(url)} {width}w")

            if srcsets:
                width = img.width
                srcsets.append(f"{markupsafe.escape(self.url_for(img))} {width}w")
                res["srcset"] = ", ".join(srcsets)
                res["src"] = self.url_for(img, absolute=absolute)
            else:
                res["width"] = str(img.width)
                res["height"] = str(img.height)
                res["src"] = self.url_for(img, absolute=absolute)

        return res

    def check(self, checker):
        pass

    def __str__(self):
        if hasattr(self, "src"):
            return self.site_path
        else:
            return self.TYPE

    def __repr__(self):
        if hasattr(self, "src"):
            if self.src:
                return f"{self.TYPE}:{self.src.relpath}"
            else:
                return f"{self.TYPE}:auto:{self.site_path}"
        else:
            return self.TYPE

    @jinja2.pass_context
    def html_full(self, context, **kw) -> str:
        """
        Render the full page, from the <html> tag downwards.
        """
        context = dict(context)
        context["render_style"] = "full"
        context.update(kw)
        return self.render_template(self.page_template, template_args=context)

    @jinja2.pass_context
    def html_body(self, context, **kw) -> str:
        """
        Render the full body of the page, with UI elements excluding
        navigation, headers, footers
        """
        return ""

    @jinja2.pass_context
    def html_inline(self, context, **kw) -> str:
        """
        Render the content of the page to be shown inline, like in a blog page.

        Above-the-fold content only, small images, no UI elements
        """
        return ""

    @jinja2.pass_context
    def html_feed(self, context, **kw) -> str:
        """
        Render the content of the page to be shown in a RSS/Atom feed.

        It shows the whole contents, without any UI elements, and with absolute
        URLs
        """
        return ""

    def to_dict(self):
        from .utils import dump_meta
        res = {
            "meta": dump_meta(self.meta),
            "type": self.TYPE,
            "site_path": self.site_path,
            "build_path": self.build_path,
        }
        if self.src:
            res["src"] = {
                "relpath": str(self.src.relpath),
                "abspath": str(self.src.abspath),
            }
        return res

    def render(self, **kw) -> RenderedElement:
        return RenderedString(self.html_full(kw))

    def render_template(self, template: jinja2.Template, template_args: Dict[Any, Any] = None) -> str:
        """
        Render a jinja2 template, logging things if something goes wrong
        """
        if template_args is None:
            template_args = {}
        template_args["page"] = self
        # try:
        return template.render(**template_args)
        # except jinja2.TemplateError as e:
        #     log.error("%s: failed to render %s: %s",
        #               template.filename, self.src.relpath if self.src else repr(self), e)
        #     log.debug("%s: failed to render %s: %s",
        #               template.filename, self.src.relpath if self.src else repr(self), e, exc_info=True)
        #     # TODO: return a "render error" page? But that risks silent errors
        #     return None

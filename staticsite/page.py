from __future__ import annotations

import collections.abc
import datetime
import enum
import logging
import os
from functools import cached_property
from typing import (TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar,
                    Union, cast)
from urllib.parse import urlparse, urlunparse

import jinja2
import markupsafe

from . import fields
from .node import Path
from .render import RenderedString
from .site import SiteElement

if TYPE_CHECKING:
    from .file import File
    from .node import Node
    from .render import RenderedElement
    from .site import Site

log = logging.getLogger("page")


class ChangeExtent(enum.IntEnum):
    """
    What kind of changes happened on this page since last build
    """
    # Page is unchanged
    UNCHANGED = 0
    # Page changed in contents but not in metadata
    CONTENTS = 1
    # Page changed completely
    ALL = 2


class PageNotFoundError(Exception):
    pass


class PageValidationError(Exception):
    def __init__(self, page: "Page", msg: str):
        self.page = page
        self.msg = msg


class PageMissesFieldError(PageValidationError):
    def __init__(self, page: "Page", field: str):
        super().__init__(page, f"missing required field meta.{field}")


P = TypeVar("P", bound="Page")
V = TypeVar("V")


class CrossreferenceField(fields.Field[P, V]):
    """
    Call crossreference() on the page when this field is set
    """
    def __set__(self, page: P, value: Any) -> None:
        page.site.pages_to_crossreference.add(page)
        super().__set__(page, value)


class Pages(collections.abc.Sequence):
    """
    List of pages, resolved at `crossreference` time, that can be provided as:
     - path to another page, relative to this page
     - page filter
    """
    def __init__(self, page: Page, value: Any):
        # Reference page for resolving relative paths
        self.page = page

        # Resolved list of pages
        self.pages: Optional[list[Page]] = None

        # Filter expression to enumerate pages
        self.query: Optional[dict[str, Any]] = None

        if isinstance(value, str):
            self.query = {"path": value}
        elif isinstance(value, list):
            self.pages = value
        elif isinstance(value, dict):
            self.query = value
        elif isinstance(value, Pages):
            self.page = value.page
            self.pages = value.pages
            self.query = value.query
        else:
            raise RuntimeError("pages field is not string, list of pages, or dict")

    def resolve(self):
        """
        Fill self.pages using self.query
        """
        if self.pages is not None:
            return

        if self.query is None:
            self.pages = []
            return

        # Replace the dict with the expanded list of pages
        # Do not include self in the result list
        self.pages = [p for p in self.page.find_pages(**self.query) if p != self.page]

    def to_dict(self) -> Optional[list[Page]]:
        return self.pages

    def __repr__(self):
        if self.pages is None:
            return repr(self.query)
        else:
            return repr(self.pages)

    def __eq__(self, other):
        if isinstance(other, list):
            return self.pages == other
        elif isinstance(other, dict):
            return self.query == other
        elif isinstance(other, Pages):
            return self.page == other.page and self.query == other.query or self.pages == other.pages
        else:
            return False

    def __len__(self):
        if self.pages is None:
            raise RuntimeError(f"{self.page}.pages is accessed before the crossreference step has run")
        return len(self.pages)

    def __getitem__(self, key):
        if self.pages is None:
            raise RuntimeError(f"{self.page}.pages is accessed before the crossreference step has run")
        return self.pages.__getitem__(key)

    def __iter__(self):
        if self.pages is None:
            raise RuntimeError(f"{self.page}.pages is accessed before the crossreference step has run")
        return self.pages.__iter__()

    def __reversed__(self):
        if self.pages is None:
            raise RuntimeError(f"{self.page}.pages is accessed before the crossreference step has run")
        return self.pages.__reversed__()


class PagesField(CrossreferenceField["Page", Pages]):
    """
    The `pages` metadata can use to select a set of pages shown by the current
    page. Although default `page.html` template will not do anything with them,
    other page templates, like `blog.html`, use this to select the pages to show.

    The `pages` feature allows defining a [page filter](page-filter.md) in the
    `pages` metadata element, which will be replaced with a list of matching pages.

    To select pages, the `pages` metadata is set to a dictionary that select pages
    in the site, with the `path`, and taxonomy names arguments similar to the
    `site_pages` function in [templates](templates.md).

    See [Selecting pages](page-filter.md) for details.
    """
    def _clean(self, page: Page, value: Any) -> Pages:
        return Pages(page, value)


class TemplateField(fields.Field["Page", str]):
    """
    Template name or compiled template, taking its default value from Page.TEMPLATE
    """
    def __get__(self, page: Page, type: Optional[Type] = None) -> str:
        if self.name not in page.__dict__:
            if (val := getattr(page, "TEMPLATE", None)):
                page.__dict__[self.name] = val
                return val
            else:
                return self.default
        else:
            return page.__dict__[self.name]


class PageDate(fields.Date["Page"]):
    """
    Make sure, on page load, that the element is a valid aware datetime object
    """
    def __get__(self, page: Page, type: Optional[Type] = None) -> Any:
        if (date := page.__dict__.get(self.name)) is None:
            if (src := getattr(page, "src", None)) is not None and src.stat is not None:
                date = page.site.localized_timestamp(src.stat.st_mtime)
            else:
                date = page.site.generation_time
            page.__dict__[self.name] = date
        return date


class Draft(fields.Bool["SourcePage"]):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def __get__(self, page: SourcePage, type: Optional[Type] = None) -> Any:
        if (value := page.__dict__.get(self.name)) is None:
            value = page.date > page.site.generation_time
            page.__dict__[self.name] = value
            return value
        else:
            return value


class RenderedField(fields.Field["Page", str]):
    """
    Field whose value is rendered from other fields
    """
    def __get__(self, page: Page, type: Optional[Type] = None) -> str:
        if (value := page.__dict__.get(self.name)) is None:
            if (tpl := getattr(page, "template_" + self.name, None)):
                # If a template exists, render it
                # TODO: remove meta= and make it compatibile again with stable staticsite
                value = markupsafe.Markup(tpl.render(meta=page.meta, page=page))
            else:
                value = self.default
            self.__dict__[self.name] = value
        return value


class RenderedTitleField(fields.Field["Page", str]):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def __get__(self, page: Page, type: Optional[Type] = None) -> str:
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


class RelatedField(fields.Field["Page", Related]):
    """
    Contains related pages indexed by name
    """
    def __get__(self, page: Page, type: Optional[Type] = None) -> Related:
        if (value := page.__dict__.get(self.name)) is None:
            value = Related(page)
            page.__dict__[self.name] = value
        return value

    def __set__(self, page: Page, value: Related) -> None:
        related = self.__get__(page)
        related.pages.update(value)


class Meta:
    """
    Read-only dict accessor to Page's fields
    """
    def __init__(self, page: Page):
        self._page = page

    def __getitem__(self, key: str) -> Any:
        if (field := self._page._fields.get(key)) is None:
            raise KeyError(key)

        if field.internal:
            raise KeyError(key)

        try:
            res = getattr(self._page, key)
            # print(f"{self._page!r} meta[{key!r}] = {res!r}")
            return res
        except AttributeError:
            raise KeyError(key)

    def __contains__(self, key: str):
        if (field := self._page._fields.get(key)) is None:
            return False
        if field.internal:
            return False

        return getattr(self._page, key) is not None

    def get(self, key: str, default: Any = None) -> Any:
        if (field := self._page._fields.get(key)) is None:
            return default
        if field.internal:
            return default

        return getattr(self._page, key, default)

    def to_dict(self) -> dict[str, Any]:
        """
        Return a dict with all the values of this Meta, including the inherited
        ones
        """
        res = {}
        for key, field in self._page._fields.items():
            if field.internal:
                continue
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

    date = PageDate(doc="""
        Publication date for the page.

        A python datetime object, timezone aware. If the date is in the future when
        `ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
        --draft` to also consider draft pages.

        If missing, the modification time of the file is used.
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

    indexed = fields.Bool["Page"](default=False, doc="""
        If true, the page appears in [directory indices](dir.md) and in
        [page filter results](page_filter.md).

        It defaults to true at least for [Markdown](markdown.md),
        [reStructuredText](rst.rst), and [data](data.md) pages.
    """)

    pages = PagesField(structure=True)

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
            search_root_node: Node,
            dst: str,
            leaf: bool,
            directory_index: bool = False,
            **kw):
        # Set these fields early as they are used by __str__/__repr__
        # Node where this page is installed in the rendered structure
        self.node: Node = node

        super().__init__(site, **kw)

        # Read-only, dict-like accessor to the page's fields
        self.meta: Meta = Meta(self)
        # Node to use as initial node for find_pages
        self.search_root_node: Node = search_root_node
        # Name of the file used to render this page on build
        self.dst: str = dst
        # Set to True if this page is a directory index. This affects the root
        # of page lookups relative to this page
        self.directory_index: bool = directory_index
        # Set to True if this page is shown as a file url, False if it's shown
        # as a path url
        self.leaf: bool = leaf

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

    def find_pages(
            self,
            path: Optional[str] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None,
            **kw) -> List["Page"]:
        """
        If not set, default root to the path of the containing directory for
        this page
        """
        from .page_filter import PageFilter
        f = PageFilter(self.site, path, limit, sort, root=self.search_root_node, **kw)
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
            if static:
                root = self.site.static_root
            else:
                root = self.site.root
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

        dest_parsed = urlparse(dest)

        return urlunparse(
            (dest_parsed.scheme, dest_parsed.netloc, dest_parsed.path,
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

    def crossreference(self) -> None:
        """
        Called at the beginning of the 'crossreference' step when the page is in
        site.pages_to_crossreference
        """
        if self.pages is not None:
            self.pages.resolve()

        if self.pages:
            # Update the page date to the max of the pages dates
            max_date = max(p.date for p in self.pages)
            self.date = max(max_date, self.date)

    def render(self, **kw) -> RenderedElement:
        """
        Return a RenderedElement that can produce the built version of this page
        """
        raise NotImplementedError(f"{self.__class__.__name__}.render not implemented")

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

    def _compute_change_extent(self) -> ChangeExtent:
        """
        Check how much this page has changed since the last build
        """
        return ChangeExtent.UNCHANGED

    @cached_property
    def change_extent(self) -> ChangeExtent:
        """
        How much this page has changed since the last build
        """
        if self.site.last_load_step < self.site.LOAD_STEP_CROSSREFERENCE:
            raise RuntimeError("Page.change_extent referenced before running page crossreference stage")
        return self._compute_change_extent()


class SourcePage(Page):
    """
    Page loaded from site sources
    """
    draft = Draft(doc="""
If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.

It defaults to false, or true if `meta.date` is in the future.
""")

    old_footprint = fields.Field["SourcePage", Optional[dict[str, Any]]](internal=True, doc="""
        Cached footprint from the previous run, or None
    """)

    def __init__(
            self, site: Site, *,
            node: Node,
            src: File,
            **kw):
        super().__init__(site, parent=node, node=node, **kw)
        self.src = src

    def _compute_footprint(self) -> dict[str, Any]:
        """
        Return a dict with information that can be used to evaluate changes in
        incremental builds
        """
        if self.site.last_load_step < self.site.LOAD_STEP_CROSSREFERENCE:
            raise RuntimeError("SourcePage._compute_footprint referenced before running page crossreference stage")
        res = {
            "mtime": self.src.stat.st_mtime,
            "size": self.src.stat.st_size,
        }
        # We can cast to list[Page] since we made sure we only run after the crossreference stage
        if (pages := cast(list[Page], self.pages)):
            res["pages"] = [page.src.relpath for page in pages if getattr(page, "src", None)]
        return res

    @cached_property
    def footprint(self) -> dict[str, Any]:
        """
        Dict with information that can be used to evaluate changes in
        incremental builds
        """
        return self._compute_footprint()

    def _compute_change_extent(self) -> ChangeExtent:
        res = super()._compute_change_extent()
        if (old := self.old_footprint) is None:
            return ChangeExtent.ALL
        if old.get("mtime") < self.footprint["mtime"] or old.get("size") != self.footprint["size"]:
            return ChangeExtent.ALL
        if res == ChangeExtent.UNCHANGED and self.footprint and self.old_footprint:
            if set(self.footprint.get("pages", ())) != set(self.old_footprint.get("pages", ())):
                return ChangeExtent.ALL
        return res


class AutoPage(Page):
    """
    Autogenerated page
    """
    created_from = fields.Field["AutoPage", Page](doc="""
        Page that generated this page.

        This is only set in autogenerated pages.
    """)

    def __init__(
            self, site: Site, *,
            created_from: Optional[Page] = None,
            **kw):
        if created_from is None:
            raise RuntimeError("created_from is None in AutoPage")
        super().__init__(site, parent=created_from, created_from=created_from, **kw)
        # TODO: remove this
        self.src = None


class FrontMatterPage(SourcePage):
    """
    Page with a front matter in its sources
    """
    front_matter = fields.Field["FrontMatterPage", dict[str, Any]](internal=True, doc="""
        Front matter as parsed by the source file
    """)

    def _compute_footprint(self) -> dict[str, Any]:
        res = super()._compute_footprint()
        fm = {}
        for k, v in self.front_matter.items():
            if isinstance(v, datetime.datetime):
                fm[k] = v.strftime("%Y-%m-%d %H:%M:%S %Z")
            else:
                fm[k] = v
        res["fm"] = fm
        return res

    def _compute_change_extent(self) -> ChangeExtent:
        res = super()._compute_change_extent()
        if res == ChangeExtent.UNCHANGED:
            return res
        if self.old_footprint is not None and self.footprint["fm"] == self.old_footprint.get("fm"):
            return ChangeExtent.CONTENTS
        else:
            return ChangeExtent.ALL


class TemplatePage(Page):
    """
    Page that renders using a Jinja2 template
    """

    template = TemplateField(doc="""
        Template used to render the page. Defaults to `page.html`, although specific
        pages of some features can default to other template names.

        Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).
    """)

    @cached_property
    def page_template(self):
        template = self.meta["template"]
        if isinstance(template, jinja2.Template):
            return template
        return self.site.theme.jinja2.get_template(template)

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
                if rel.TYPE not in ("image", "scaledimage"):
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

    def render(self, **kw) -> RenderedElement:
        return RenderedString(self.html_full(kw))

    def render_template(self, template: jinja2.Template, template_args: Optional[dict[Any, Any]] = None) -> str:
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

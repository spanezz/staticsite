from __future__ import annotations

import collections.abc
import datetime
import enum
import logging
import os
from functools import cached_property
from typing import (TYPE_CHECKING, Any, Iterator, Optional, Sequence, Type,
                    TypeVar, Union, cast, overload)

import jinja2
import markupsafe

from . import fields
from .render import RenderedString
from .site import Path, SiteElement
from .utils.arrange import arrange

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


class OptionalPageField(fields.Field[P, Optional["Page"]]):
    """
    Field containing a Page
    """
    def _clean(self, page: P, value: Any) -> Optional[Page]:
        if value is None:
            return None
        elif isinstance(value, Page):
            return value
        else:
            raise TypeError(
                    f"invalid value of type {type(value)} for {page!r}.{self.name}:"
                    " expecting, None or Page")


class Pages(collections.abc.Sequence["Page"]):
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

    def resolve(self) -> None:
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

    def __repr__(self) -> str:
        if self.pages is None:
            return repr(self.query)
        else:
            return repr(self.pages)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, list):
            return self.pages == other
        elif isinstance(other, dict):
            return self.query == other
        elif isinstance(other, Pages):
            return self.page == other.page and self.query == other.query or self.pages == other.pages
        else:
            return False

    def __len__(self) -> int:
        if self.pages is None:
            raise RuntimeError(f"{self.page}.pages is accessed before the crossreference step has run")
        return len(self.pages)

    @overload
    def __getitem__(self, int, /) -> Page:
        ...

    @overload
    def __getitem__(self, slice, /) -> Sequence[Page]:
        ...

    def __getitem__(self, key: Union[int, slice], /) -> Union[Page, Sequence[Page]]:
        if self.pages is None:
            raise RuntimeError(f"{self.page}.pages is accessed before the crossreference step has run")
        return self.pages.__getitem__(key)

    def __iter__(self) -> Iterator[Page]:
        if self.pages is None:
            raise RuntimeError(f"{self.page}.pages is accessed before the crossreference step has run")
        return self.pages.__iter__()

    def __reversed__(self) -> Iterator[Page]:
        if self.pages is None:
            raise RuntimeError(f"{self.page}.pages is accessed before the crossreference step has run")
        return self.pages.__reversed__()

    def arrange(self, sort: str, limit: Optional[int] = None) -> list[Page]:
        """
        Sort the pages by ``sort`` and take the first ``limit`` ones
        """
        if self.pages is None:
            raise RuntimeError(f"{self.page}.arrange is accessed before the crossreference step has run")
        return arrange(self.pages, sort=sort, limit=limit)


class PagesField(CrossreferenceField["Page", Pages]):
    """
    The `pages` metadata can use to select a set of pages shown by the current
    page. Although default `page.html` template will not do anything with them,
    other page templates, like `blog.html`, use this to select the pages to show.

    The `pages` field allows defining a [page filter](../page-filter.md) which
    will be replaced with a list of matching pages.

    To select pages, the `pages` metadata is set to a dictionary that select pages
    in the site, with the `path`, and taxonomy names arguments similar to the
    `site_pages` function in [templates](../templates.md).

    See [Selecting pages](../page-filter.md) for details.

    ## Example blog page

    ```jinja2
    {% extends "base.html" %}

    {% block front_matter %}
    ---
    pages:
      path: blog/*
      limit: 10
      sort: "-date"
    syndication:
      add_to:
        path: blog/*
      title: "Enrico's blog feed"
    {% endblock %}

    {% import 'lib/blog.html' as blog %}

    {% block title %}Enrico's blog{% endblock %}

    {% block nav %}
    {{super()}}
    <li class="nav-item"><a class="nav-link" href="{{ url_for('/blog/archive.html') }}">Archive</a></li>
    {% endblock %}

    {% block content %}

    <h1 class="display-4">Last 10 blog posts</h1>

    {{blog.pages(page)}}

    {% endblock %}
    ```
    """
    def _clean(self, page: Page, value: Any) -> Pages:
        return Pages(page, value)


class TemplateField(fields.Field["TemplatePage", Union[str, jinja2.Template]]):
    """
    Template name or compiled template, taking its default value from Page.TEMPLATE
    """
    def __get__(self, page: "TemplatePage", type: Optional[Type] = None) -> Union[str, jinja2.Template]:
        if self.name not in page.__dict__:
            page.__dict__[self.name] = page.TEMPLATE
            return page.TEMPLATE
        else:
            return cast(str, page.__dict__[self.name])

    def _clean(self, obj: Page, value: Any) -> Union[str, jinja2.Template]:
        if isinstance(value, str):
            return value
        elif isinstance(value, jinja2.Template):
            return value
        else:
            raise TypeError(
                    f"invalid value of type {type(value)} for {obj!r}.{self.name}:"
                    " expecting str or jinja2.Template")


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


class RenderedField(fields.Str["Page"]):
    """
    Field whose value is rendered from other fields
    """
    def __get__(self, page: Page, type: Optional[Type] = None) -> Optional[str]:
        if (cur := page.__dict__.get(self.name)) is None:
            value: str
            if (tpl := getattr(page, "template_" + self.name, None)):
                # If a template exists, render it
                value = markupsafe.Markup(tpl.render(page=page))
                self.__dict__[self.name] = value
                return value
            elif self.default is not None:
                self.__dict__[self.name] = self.default
                return self.default
            else:
                return None
        else:
            return cast(str, cur)


class RenderedTitleField(fields.Str["Page"]):
    """
    Render the tile for a page, defaulting to site_name if missing
    """
    def __get__(self, page: Page, type: Optional[Type] = None) -> str:
        if (cur := page.__dict__.get(self.name)) is None:
            value: str
            if (tpl := getattr(page, "template_" + self.name, None)):
                # If a template exists, render it
                value = markupsafe.Markup(tpl.render(page=page))
            elif page.site_name is None:
                raise RuntimeError("site_name not set")
            else:
                value = page.site_name
            self.__dict__[self.name] = value
            return value
        else:
            return cast(str, cur)


class Related(collections.abc.MutableMapping[str, "Page"]):
    """
    Container for related pages
    """
    def __init__(self, page: Page):
        self.page = page
        self.pages: dict[str, Union[str, Page]] = {}

    def __repr__(self) -> str:
        return f"Related({self.page!r}, {self.pages!r}))"

    def __str__(self) -> str:
        return self.pages.__str__()

    def __getitem__(self, name: str, /) -> Page:
        val = self.pages[name]

        if isinstance(val, str):
            page = self.page.resolve_path(val)
            self.pages[name] = page
            return page
        else:
            return val

    def __setitem__(self, name: str, page: Union[str, Page]) -> None:
        if (old := self.pages.get(name)) is not None and old != self.page:
            log.warn("%s: attempt to set related.%s to %r but it was already %r",
                     self, name, page, old)
            return
        self.pages[name] = page

    def __delitem__(self, name: str, /) -> None:
        self.pages.__delitem__(name)

    def __len__(self) -> int:
        return self.pages.__len__()

    def __iter__(self) -> Iterator[str]:
        return self.pages.__iter__()

    def to_dict(self) -> dict[str, Any]:
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
    Readonly mapping of pages related to this page, indexed by name.

    If there are no related pages, `page.meta.related` will be guaranteed to exist
    as an empty dictionary.

    Features can add to this. For example, [syndication](syndication.md) can add
    `meta.related.archive`, `meta.related.rss`, and `meta.related.atom`.
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

    def __contains__(self, key: str) -> bool:
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

    related = RelatedField(structure=True)

    def __init__(
            self, site: Site, *,
            node: Node,
            search_root_node: Node,
            dst: str,
            leaf: bool,
            directory_index: bool = False,
            **kw) -> None:
        # Set these fields early as they are used by __str__/__repr__

        # Node where this page is installed in the rendered structure
        self.node: Node = node

        # Set to True if this page is shown as a file url, False if it's shown
        # as a path url
        self.leaf: bool = leaf

        # Name of the file used to render this page on build
        self.dst: str = dst

        super().__init__(site, **kw)

        # Read-only, dict-like accessor to the page's fields
        self.meta: Meta = Meta(self)
        # Node to use as initial node for find_pages
        self.search_root_node: Node = search_root_node
        # Set to True if this page is a directory index. This affects the root
        # of page lookups relative to this page
        self.directory_index: bool = directory_index
        # Basename of this page in the source tree, or None if it's an
        # autogenerated page
        self.source_name: Optional[str] = None

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
            return os.path.join(self.node.path, self.dst)
        else:
            return self.node.path

    def add_related(self, name: str, page: "Page") -> None:
        """
        Set the page as meta.related.name
        """
        self.related[name] = page

    def find_pages(
            self,
            path: Optional[str] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None,
            **kw) -> list["Page"]:
        """
        If not set, default root to the path of the containing directory for
        this page
        """
        from .page_filter import PageFilter
        f = PageFilter(self.site, path, limit, sort, root=self.search_root_node, **kw)
        return f.filter()

    def lookup_page(self, path: Path) -> Optional[Page]:
        return self.search_root_node.lookup_page(path)

    def url_for(self, target: Union[str, "Page"], absolute: bool = False, static: bool = False) -> str:
        """
        Generate a URL for a page, specified by:

        * an absolute path
        * a path relative to this page
        * the target page itself
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

        if self.site.root.site_path:
            path = os.path.join(self.site.root.site_path, page.site_path).strip("/")
        else:
            path = page.site_path.strip("/")

        if absolute:
            if page.site_url is None:
                raise RuntimeError("site_url is None")
            site_url = page.site_url.rstrip("/")
            return f"{site_url}/{path}"
        else:
            return "/" + path

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

    def __str__(self) -> str:
        return self.site_path

    def __repr__(self) -> str:
        return f"{self.TYPE}:auto:{self.site_path}"

    def to_dict(self) -> dict[str, Any]:
        from .utils import dump_meta
        res = {
            "meta": dump_meta(self.meta),
            "type": self.TYPE,
            "site_path": self.site_path,
            "build_path": os.path.join(self.node.path, self.dst),
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
        # Information about the source file for this page
        # Set right away so that __repr__ works
        self.src: File = src
        super().__init__(site, parent=node, node=node, **kw)
        self.source_name: str = os.path.basename(self.src.relpath)

    def __str__(self) -> str:
        return self.site_path

    def __repr__(self) -> str:
        return f"{self.TYPE}:{self.src.relpath}"

    def to_dict(self) -> dict[str, Any]:
        res = super().to_dict()
        res["src"] = {
            "relpath": str(self.src.relpath),
            "abspath": str(self.src.abspath),
        }
        return res

    def _compute_footprint(self) -> dict[str, Any]:
        """
        Return a dict with information that can be used to evaluate changes in
        incremental builds
        """
        if self.site.last_load_step < self.site.LOAD_STEP_CROSSREFERENCE:
            raise RuntimeError("SourcePage._compute_footprint referenced before running page crossreference stage")
        res: dict[str, Any] = {
            "mtime": self.src.stat.st_mtime,
            "size": self.src.stat.st_size,
        }
        # We can cast to list[Page] since we made sure we only run after the crossreference stage
        if (pages := self.pages):
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
    created_from = OptionalPageField["AutoPage"](doc="""
        Page that generated this page.

        This is only set in autogenerated pages.
    """)

    def __init__(
            self, site: Site, *,
            created_from: Optional[Page] = None,
            **kw: Any) -> None:
        if created_from is None:
            raise RuntimeError("created_from is None in AutoPage")
        super().__init__(site, parent=created_from, created_from=created_from, **kw)


class FrontMatterPage(SourcePage):
    """
    Page with a front matter in its sources
    """
    front_matter = fields.Dict["FrontMatterPage"](internal=True, doc="""
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
    # Default page template
    TEMPLATE = "page.html"

    template = TemplateField(doc="""
        Template used to render the page. Defaults to `page.html`, although specific
        pages of some features can default to other template names.

        Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).
    """)

    @cached_property
    def page_template(self) -> jinja2.Template:
        template = self.meta["template"]
        if isinstance(template, jinja2.Template):
            return template
        return self.site.theme.jinja2.get_template(template)

    @jinja2.pass_context
    def html_full(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        """
        Render the full page, from the <html> tag downwards.
        """
        context = dict(context)
        context["render_style"] = "full"
        context.update(kw)
        return self.render_template(self.page_template, template_args=context)

    @jinja2.pass_context
    def html_body(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        """
        Render the full body of the page, with UI elements excluding
        navigation, headers, footers
        """
        return ""

    @jinja2.pass_context
    def html_inline(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        """
        Render the content of the page to be shown inline, like in a blog page.

        Above-the-fold content only, small images, no UI elements
        """
        return ""

    @jinja2.pass_context
    def html_feed(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        """
        Render the content of the page to be shown in a RSS/Atom feed.

        It shows the whole contents, without any UI elements, and with absolute
        URLs
        """
        return ""

    def render(self, **kw: Any) -> RenderedElement:
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


class ImagePage(Page):
    width = fields.Int[Page](doc="""
        Image width
    """)
    height = fields.Int[Page](doc="""
        Image height
    """)

    def get_img_attributes(
            self, type: Optional[str] = None, absolute=False) -> dict[str, str]:
        """
        Given a path to an image page, return a dict with <img> attributes that
        can be used to refer to it
        """
        res = {
            "alt": self.title,
        }

        if type is not None:
            # If a specific version is required, do not use srcset
            rel = self.related.get(type, self)
            res["width"] = str(rel.width)
            res["height"] = str(rel.height)
            res["src"] = self.url_for(rel, absolute=absolute)
        else:
            # https://developers.google.com/web/ilt/pwa/lab-responsive-images
            # https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Responsive_images
            srcsets = []
            for rel in self.related.values():
                if rel.TYPE not in ("image", "scaledimage"):
                    continue

                if (width := rel.width) is None:
                    continue

                url = self.url_for(rel, absolute=absolute)
                srcsets.append(f"{markupsafe.escape(url)} {width}w")

            if srcsets:
                width = self.width
                srcsets.append(f"{markupsafe.escape(self.url_for(self))} {width}w")
                res["srcset"] = ", ".join(srcsets)
                res["src"] = self.url_for(self, absolute=absolute)
            else:
                res["width"] = str(self.width)
                res["height"] = str(self.height)
                res["src"] = self.url_for(self, absolute=absolute)

        return res

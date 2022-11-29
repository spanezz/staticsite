from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any, Optional, Union, List
import os
import logging
import warnings
from urllib.parse import urlparse, urlunparse
from .utils import lazy
from .render import RenderedString
import jinja2
import markupsafe

if TYPE_CHECKING:
    from . import structure
    from .render import RenderedElement
    from .site import Site
    from .file import File
    from .metadata import Meta

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


class Page:
    """
    A source page in the site.

    This can be a static asset, a file to be rendered, a taxonomy, a
    directory listing, or anything else.
    """
    # Page type
    TYPE: str

    def __init__(
            self, site: Site, *,
            meta: Meta,
            src: Optional[File] = None,
            created_from: Optional["Page"] = None):
        # Site for this page
        self.site = site
        # structure.Node where this page is installed in the rendered structure
        self.node: Optional[structure.Node] = None
        # Node with the subtree rooted on this page in the site hierarchy
        self.site_dir: Optional[structure.Node] = None
        # File object for this page on disk, or None if this is an autogenerated page
        self.src = src
        # A dictionary with the page metadata. See the README for documentation
        # about its contents.
        self.meta: Meta = meta

        # True if this page can render a short version of itself
        self.content_has_split = False

    @classmethod
    def create_from(cls, page: "Page", meta: Meta, **kw):
        """
        Generate this page derived from an existing one
        """
        # If page is the root dir, it has dir set to None, and we can use it as dir
        new_meta = page.meta.derive()
        new_meta.update(meta.values)
        new_meta["created_from"] = page
        return cls(page.site, src=page.src, meta=new_meta, created_from=page, **kw)

    @property
    def created_from(self) -> Optional[Page]:
        """
        Legacy accessor for self.meta.get("created_from")
        """
        warnings.warn("use page.meta.get('created_from') instead of page.created_from", DeprecationWarning)
        return self.meta.get("created_from")

    @property
    def build_path(self) -> str:
        """
        Accessor to support the migration away from meta['build_path']
        """
        # return self.meta["build_path"]
        return self.node.compute_build_path()

    def add_related(self, name: str, page: "Page"):
        """
        Set the page as meta.related.name
        """
        related = self.meta.get("related")
        if related is None:
            self.meta["related"] = related = {}
        old = related.get(name)
        if old is not None:
            log.warn("%s: attempt to set related.%s to %r but it was already %r",
                     self, name, page, old)
            return
        related[name] = page

    def validate(self):
        """
        Enforce common meta invariants.

        Performs validation and completion of metadata.

        Raises PageValidationError or one of its subclasses of the page should
        not be added to the site.
        """
        # Run metadata on load functions
        self.site.metadata.on_load(self)

        # TODO: move more of this to on_load functions?

        # title must exist
        if "title" not in self.meta:
            self.meta["title"] = self.meta["site_name"]

        # Check the existence of other mandatory fields
        if "site_url" not in self.meta:
            raise PageMissesFieldError(self, "site_url")

        # Make sure site_path exists and is relative
        site_path = self.meta.get("site_path")
        if site_path is None:
            raise PageMissesFieldError(self, "site_path")

    @lazy
    def page_template(self):
        template = self.meta["template"]
        if isinstance(template, jinja2.Template):
            return template
        return self.site.theme.jinja2.get_template(template)

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
        if root is None and self.node is not None and self.node.src is not None and self.node.src.relpath:
            root = self.node.src.relpath

        from .page_filter import PageFilter
        f = PageFilter(self.site, path, limit, sort, root=root, **kw)
        return f.filter(self.site.structure.pages.values())

    def resolve_path(self, target: Union[str, "Page"]) -> "Page":
        """
        Return a Page from the site, given a source or site path relative to
        this page.

        The path is resolved relative to this page, and if not found, relative
        to the parent page, and so on until the top.
        """
        if isinstance(target, Page):
            return target

        # Absolute URLs are resolved as is
        if target.startswith("/"):
            target_relpath = os.path.normpath(target)

            # Try by source path
            # src.relpath is indexed without leading / in site
            res = self.site.structure.pages_by_src_relpath.get(target_relpath.lstrip("/"))
            if res is not None:
                return res

            # Try by site path
            res = self.site.structure.pages.get(target_relpath)
            if res is not None:
                return res

            # Try adding STATIC_PATH as a compatibility with old links
            target_relpath = os.path.join(self.site.settings.STATIC_PATH, target_relpath.lstrip("/"))

            # Try by source path
            res = self.site.structure.pages_by_src_relpath.get(target_relpath)
            if res is not None:
                log.warn("%s: please use %s instead of %s", self, target_relpath, target)
                return res

            log.warn("%s: cannot resolve path %s", self, target)
            raise PageNotFoundError(f"cannot resolve absolute path {target}")

        # Relative urls are tried based on all path components of this page,
        # from the bottom up

        # First using the source paths
        if self.src is not None:
            if (dir_path := os.path.dirname(self.src.relpath)):
                root = os.path.join("/", dir_path)
            else:
                root = "/"

            target_relpath = os.path.normpath(os.path.join(root, target))
            res = self.site.structure.pages_by_src_relpath.get(target_relpath.lstrip("/"))
            if res is not None:
                return res

        # Finally, using the site paths
        root = self.meta["site_path"]
        target_relpath = os.path.normpath(os.path.join(root, target))
        res = self.site.structure.pages.get(target_relpath)
        if res is not None:
            return res

        raise PageNotFoundError(f"cannot resolve `{target!r}` relative to `{self!r}`")

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

    def url_for(self, target: Union[str, "Page"], absolute=False) -> str:
        """
        Generate a URL for a page, specified by path or with the page itself
        """
        page: "Page"

        if isinstance(target, str):
            page = self.resolve_path(target)
        else:
            page = target

        # If the destination has a different site_url, generate an absolute url
        if self.meta["site_url"] != page.meta["site_url"]:
            absolute = True

        if absolute:
            site_url = page.meta["site_url"].rstrip("/")
            return f"{site_url}{page.meta['site_path']}"
        else:
            return page.meta["site_path"]

    def get_img_attributes(
            self, image: Union[str, "Page"], type: Optional[str] = None, absolute=False) -> Dict[str, str]:
        """
        Get <img> attributes into the given dict
        """
        img = self.resolve_path(image)

        res = {
            "alt": img.meta["title"],
        }

        if type is not None:
            # If a specific version is required, do not use srcset
            rel = img.meta["related"].get(type, img)
            res["width"] = str(rel.meta["width"])
            res["height"] = str(rel.meta["height"])
            res["src"] = self.url_for(rel, absolute=absolute)
        else:
            # https://developers.google.com/web/ilt/pwa/lab-responsive-images
            # https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Responsive_images
            srcsets = []
            for rel in img.meta["related"].values():
                if rel.TYPE != "image":
                    continue

                width = rel.meta.get("width")
                if width is None:
                    continue

                url = self.url_for(rel, absolute=absolute)
                srcsets.append(f"{markupsafe.escape(url)} {width}w")

            if srcsets:
                width = img.meta["width"]
                srcsets.append(f"{markupsafe.escape(self.url_for(img))} {width}w")
                res["srcset"] = ", ".join(srcsets)
                res["src"] = self.url_for(img, absolute=absolute)
            else:
                res["width"] = str(img.meta["width"])
                res["height"] = str(img.meta["height"])
                res["src"] = self.url_for(img, absolute=absolute)

        return res

    def check(self, checker):
        pass

    def __str__(self):
        return self.meta["site_path"]

    def __repr__(self):
        if self.src:
            return f"{self.TYPE}:{self.src.relpath}"
        else:
            return f"{self.TYPE}:auto:{self.meta['site_path']}"

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
        try:
            return template.render(**template_args)
        except jinja2.TemplateError as e:
            log.error("%s: failed to render %s: %s", template.filename, self.src.relpath, e)
            log.debug("%s: failed to render %s: %s", template.filename, self.src.relpath, e, exc_info=True)
            # TODO: return a "render error" page? But that risks silent errors
            return None

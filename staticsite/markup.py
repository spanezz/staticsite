from __future__ import annotations

import contextlib
import logging
from typing import (TYPE_CHECKING, Any, Generator, NamedTuple, Optional,
                    Union)
from urllib.parse import urlparse, urlunparse

from .page import PageNotFoundError, SourcePage

if TYPE_CHECKING:
    import urllib.parse

    from .page import Page

log = logging.getLogger("markdown")


class ResolvedLink(NamedTuple):
    page: Page
    site_path: str


class LinkResolver:
    """
    Caching backend for resolving internal URLs in rendered content
    """

    def __init__(self) -> None:
        self.page: Optional[Page] = None
        self.absolute: bool = False
        self.substituted: dict[str, ResolvedLink] = {}
        self.external_links: set[str] = set()

    def set_page(self, page: Page, absolute: bool = False):
        self.page = page
        self.absolute = absolute
        self.substituted = {}
        self.external_links = set()

    def load_cache(self, paths: list[tuple[str, str]]) -> bool:
        # If the destination of links has changed, drop the cached version.
        # This will as a side effect prime the link resolver cache,
        # avoiding links from being looked up again during rendering
        for src, dest in paths:
            if self.resolve_page(src)[0].site_path != dest:
                return False
        return True

    def to_cache(self) -> list[tuple[str, str]]:
        return [(k, v.site_path) for k, v in self.substituted.items()]

    def resolve_page(self, url: str) -> Union[tuple[None, None], tuple[Page, urllib.parse.ParseResult]]:
        parsed = urlparse(url)

        # If it's an absolute url, leave it unchanged
        if parsed.scheme or parsed.netloc:
            self.external_links.add(url)
            return None, None

        # If it's an anchor inside the page, leave it unchanged
        if not parsed.path:
            return None, None

        # Try with cache
        if (resolved := self.substituted.get(parsed.path)) is not None:
            return resolved.page, parsed

        # Resolve as a path
        try:
            page = self.page.resolve_path(parsed.path)
        except PageNotFoundError as e:
            log.warn("%s: %s", self.page, e)
            return None, None

        # Cache the page site_path
        self.substituted[url] = ResolvedLink(page, page.site_path)

        return page, parsed

    def resolve_url(self, url: str) -> str:
        """
        Resolve internal URLs.

        Returns None if the URL does not need changing, else returns the new URL.
        """
        page, parsed = self.resolve_page(url)
        if page is None:
            return url

        new_url = self.page.url_for(page, absolute=self.absolute)
        dest = urlparse(new_url)

        return urlunparse(
            (dest.scheme, dest.netloc, dest.path,
             parsed.params, parsed.query, parsed.fragment)
        )


class MarkupFeature:
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.link_resolver = LinkResolver()


class MarkupRenderContext:
    """
    State held during rendering of a page markup
    """
    def __init__(self, page: MarkupPage, cache_key: str):
        self.page = page
        self.link_resolver = page.feature.link_resolver
        self.cache_key = cache_key
        self.cache: dict[str, Any]

    def load(self):
        if (cache := self.page.feature.render_cache.get(self.cache_key)) is None:
            self.reset_cache()
            return

        if cache["mtime"] != self.page.src.stat.st_mtime:
            # If the source has changed, drop the cached version
            self.reset_cache()
            return

        if (paths := cache.get("paths")) is None or not self.link_resolver.load_cache(paths):
            self.reset_cache()
            return

        self.cache = cache

    def reset_cache(self):
        self.cache = {
            "mtime": self.page.src.stat.st_mtime,
        }

    def save(self):
        self.cache["paths"] = self.link_resolver.to_cache()
        self.page.feature.render_cache.put(self.cache_key, self.cache)


class MarkupPage(SourcePage):
    """
    Page which renders content from text markup.

    This is a base for pages like Markdown or Rst
    """
    def __init__(self, *, feature: MarkupFeature, **kw):
        super().__init__(**kw)
        self.feature = feature

    @contextlib.contextmanager
    def markup_render_context(
            self, cache_key: str, absolute: bool = False) -> Generator[MarkupRenderContext, None, None]:
        self.feature.link_resolver.set_page(self, absolute)
        render_context = MarkupRenderContext(self, cache_key)
        render_context.load()
        yield render_context
        render_context.save()

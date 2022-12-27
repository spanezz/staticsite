from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any, ContextManager, Optional, Union
from urllib.parse import urlparse, urlunparse

from .page import SourcePage, PageNotFoundError

if TYPE_CHECKING:
    import urllib.parse

    from .page import Page

log = logging.getLogger("markdown")


class LinkResolver:
    """
    Caching backend for resolving internal URLs in rendered content
    """

    def __init__(self):
        self.page: Optional[Page] = None
        self.absolute: bool = False
        self.substituted: dict[str, str] = {}
        self.external_links: set[str] = set()

    def set_page(self, page: Page, absolute: bool = False):
        self.page = page
        self.absolute = absolute
        self.substituted = {}
        self.external_links = set()

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
        site_path = self.substituted.get(parsed.path)
        if site_path is not None:
            try:
                return self.page.site.find_page(site_path), parsed
            except KeyError:
                log.warn("%s: url %s resolved via cache to %s which does not exist in the site. Cache out of date?",
                         self.page, url, site_path)

        # Resolve as a path
        try:
            page = self.page.resolve_path(parsed.path)
        except PageNotFoundError as e:
            log.warn("%s: %s", self.page, e)
            return None, None

        # Cache the page site_path
        self.substituted[url] = page.site_path

        return page, parsed

    def resolve_url(self, url: str) -> tuple[Page, str]:
        """
        Resolve internal URLs.

        Returns None if the URL does not need changing, else returns the new URL.
        """
        page, parsed = self.resolve_page(url)
        if page is None:
            return page, url

        new_url = self.page.url_for(page, absolute=self.absolute)
        dest = urlparse(new_url)

        return page, urlunparse(
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
        self.cache_key = cache_key
        self.cache: dict[str, Any]

    def load(self):
        if (cache := self.page.feature.render_cache.get(self.cache_key)) is None:
            self.reset_cache()
        elif cache["mtime"] != self.page.src.stat.st_mtime:
            # If the source has changed, drop the cached version
            self.reset_cache()
        else:
            self.cache = cache

    def reset_cache(self):
        self.cache = {
            "mtime": self.page.src.stat.st_mtime,
        }

    def save(self):
        self.page.feature.render_cache.put(self.cache_key, self.cache)


class MarkupPage(SourcePage):
    """
    Page which renders content from text markup.

    This is a base for pages like Markdown or Rst
    """

    @contextlib.contextmanager
    def markup_render_context(self, cache_key: str) -> ContextManager[MarkupRenderContext]:
        render_context = MarkupRenderContext(self, cache_key)
        render_context.load()
        yield render_context
        render_context.save()

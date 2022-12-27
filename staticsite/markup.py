from __future__ import annotations

import contextlib
from typing import Any, ContextManager

from .page import SourcePage


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

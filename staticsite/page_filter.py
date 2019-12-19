from __future__ import annotations
from typing import Optional, Any, Tuple, Callable, List, Iterable
from .page import Page
from . import site
from .utils import compile_page_match


def sort_args(sort: str) -> Tuple[str, bool, Callable[[Page], Any]]:
    """
    Parse a page sort string, returning a tuple of:
    * which page metadata is used for sorting, or None if sorting is not based
      on metadata
    * a bool, set to True if sort order is reversed
    * a key function for the sorting
    """
    if sort is None:
        return None, None, None

    # Process the '-'
    if sort.startswith("-"):
        reverse = True
        sort = sort[1:]
    else:
        reverse = False

    # Add a sort key function
    if sort == "url":
        sort = None

        def key(page):
            return page.dst_link
    else:
        def key(page):
            return page.meta.get(sort, None)

    return sort, reverse, key


class PageFilter:
    """
    Engine for selecting pages in the site
    """

    def __init__(
            self,
            site: "site.Site",
            path: Optional[str] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None,
            **kw):
        self.site = site

        if path is not None:
            self.re_path = compile_page_match(path)
        else:
            self.re_path = None

        self.sort_meta, self.sort_reverse, self.sort_key = sort_args(sort)

        self.taxonomy_filters = []
        for taxonomy in self.site.features["taxonomy"].taxonomies.values():
            t_filter = kw.get(taxonomy.name)
            if t_filter is None:
                continue
            self.taxonomy_filters.append((taxonomy.name, frozenset(t_filter)))

        self.limit = limit

    def filter(self, all_pages: Iterable[Page]) -> List[Page]:
        pages = []

        for page in all_pages:
            if not page.FINDABLE:
                continue
            if self.re_path is not None and not self.re_path.match(page.src.relpath):
                continue
            if self.sort_meta is not None and self.sort_meta not in page.meta:
                continue
            fail_taxonomies = False
            for name, t_filter in self.taxonomy_filters:
                page_tags = frozenset(t.name for t in page.meta.get(name, ()))
                if not t_filter.issubset(page_tags):
                    fail_taxonomies = True
            if fail_taxonomies:
                    continue
            pages.append(page)

        if self.sort_key is not None:
            pages.sort(key=self.sort_key, reverse=self.sort_reverse)

        if self.limit is not None:
            pages = pages[:self.limit]

        return pages

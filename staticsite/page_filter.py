from __future__ import annotations
from typing import Optional, Any, Tuple, Callable, List, Iterable, Union, FrozenSet
import fnmatch
import re
from .page import Page
from . import site


def compile_page_match(pattern: Union[str, re.Pattern]) -> re.Pattern:
    """
    Return a compiled re.Pattrn from a glob or regular expression.

    :arg pattern:
      * if it's a re.Pattern instance, it is returned as is
      * if it starts with ``^`` or ends with ``$``, it is compiled as a regular
        expression
      * otherwise, it is considered a glob expression, and fnmatch.translate()
        is used to convert it to a regular expression, then compiled
    """
    if hasattr(pattern, "match"):
        return pattern
    if pattern and (pattern[0] == '^' or pattern[-1] == '$'):
        return re.compile(pattern)
    return re.compile(fnmatch.translate(pattern))


def sort_args(sort: Optional[str]) -> Tuple[Optional[str], bool, Optional[Callable[[Page], Any]]]:
    """
    Parse a page sort string, returning a tuple of:
    * which page metadata is used for sorting, or None if sorting is not based
      on metadata
    * a bool, set to True if sort order is reversed
    * a key function for the sorting
    """
    if sort is None:
        return None, False, None

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
            return page.site_path
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

        self.taxonomy_filters: List[Tuple[str, FrozenSet[str]]] = []
        for taxonomy in self.site.features["taxonomy"].taxonomies.values():
            t_filter = kw.get(taxonomy.name)
            if t_filter is None:
                continue
            self.taxonomy_filters.append((taxonomy.name, frozenset(t_filter)))

        self.limit = limit

    def filter(self, all_pages: Iterable[Page]) -> List[Page]:
        pages = []

        for page in all_pages:
            if not page.meta["indexed"]:
                continue
            if self.re_path is not None:
                if page.src is None:
                    continue
                if not self.re_path.match(page.src.relpath):
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

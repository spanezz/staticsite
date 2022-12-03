from __future__ import annotations

import fnmatch
import os
import re
from typing import (TYPE_CHECKING, Any, Callable, FrozenSet, Generator,
                    Optional, Sequence, Union)

from . import site
from .page import Page

if TYPE_CHECKING:
    from . import structure


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


def sort_args(sort: Optional[str]) -> tuple[Optional[str], bool, Optional[Callable[[Page], Any]]]:
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
            root: Optional[structure.Node] = None,
            allow: Optional[Sequence[Page]] = None,
            **kw):
        self.site = site
        self.root = root

        if path is not None:
            self.re_path = compile_page_match(path)
        else:
            self.re_path = None

        self.sort_meta, self.sort_reverse, self.sort_key = sort_args(sort)

        self.taxonomy_filters: list[tuple[str, FrozenSet[str]]] = []
        for taxonomy in self.site.features["taxonomy"].taxonomies.values():
            t_filter = kw.get(taxonomy.name)
            if t_filter is None:
                continue
            self.taxonomy_filters.append((taxonomy.name, frozenset(t_filter)))

        self.limit = limit

        self.allow = allow

        # print(f"PageFilter({path=!r}, {self.root.compute_path()=!r}, {self.re_path=!r}, {self.taxonomy_filters=}")

    def filter(self):
        # print("PageFilter.filter")
        pages = []

        for page in self._filter(self.root or self.site.structure.root, relpath=""):
            pages.append(page)

        if self.sort_key is not None:
            pages.sort(key=self.sort_key, reverse=self.sort_reverse)

        if self.limit is not None:
            pages = pages[:self.limit]

        return pages

    def _filter(self, root: structure.Node, relpath: str) -> Generator[Page, None, None]:

        for name, page in root.build_pages.items():
            if not page.meta["indexed"]:
                continue
            if self.allow is not None and page not in self.allow:
                continue
            if self.sort_meta is not None and self.sort_meta not in page.meta:
                continue

            # Taxonomy_filters
            fail_taxonomies = False
            for name, t_filter in self.taxonomy_filters:
                page_tags = frozenset(t.name for t in page.meta.get(name, ()))
                if not t_filter.issubset(page_tags):
                    fail_taxonomies = True
            if fail_taxonomies:
                continue

            # print(f"_filter {page=!r} {relpath=!r} {page.dst}")

            if self.re_path is not None:
                if self.re_path.match(os.path.join(relpath, name)):
                    pass
                elif page.src and self.re_path.match(
                        (os.path.join(relpath, os.path.basename(page.src.relpath)))):
                    pass
                else:
                    # print(f"  {page=!r} {page.src=} did not match")
                    continue

            yield page

        if root.sub:
            for node in root.sub.values():
                yield from self._filter(node, relpath=os.path.join(relpath, node.name))

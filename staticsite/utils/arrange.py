from __future__ import annotations

import heapq
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..page import Page


def arrange(pages: list[Page], sort: str, limit: Optional[int] = None) -> list[Page]:
    """
    Sort the pages by ``sort`` and take the first ``limit`` ones
    """
    from ..page_filter import sort_args

    sort_meta, reverse, key = sort_args(sort)
    if key is None:
        if limit is None:
            return pages
        else:
            return pages[:limit]
    else:
        if limit is None:
            return sorted(pages, key=key, reverse=reverse)
        elif limit == 1:
            if reverse:
                return [max(pages, key=key)]
            else:
                return [min(pages, key=key)]
        elif len(pages) > 10 and limit < len(pages) / 3:
            if reverse:
                return heapq.nlargest(limit, pages, key=key)
            else:
                return heapq.nsmallest(limit, pages, key=key)
        else:
            return sorted(pages, key=key, reverse=reverse)[:limit]

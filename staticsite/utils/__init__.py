from __future__ import annotations

import contextlib
import datetime
import heapq
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union

import pytz

if TYPE_CHECKING:
    from ..page import Page

log = logging.getLogger("utils")


def format_date_rfc822(dt: datetime.datetime) -> str:
    from email.utils import formatdate
    return formatdate(dt.timestamp())


def format_date_rfc3339(dt: datetime.datetime) -> str:
    dt = dt.astimezone(pytz.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_date_w3cdtf(dt: datetime.datetime) -> str:
    offset = dt.utcoffset()
    if offset:
        offset_sec = (offset.days * 24 * 3600 + offset.seconds)
        offset_hrs = offset_sec // 3600
        offset_min = offset_sec % 3600
        tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
    else:
        tz_str = 'Z'
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + tz_str


def format_date_iso8601(dt: datetime.datetime) -> str:
    offset = dt.utcoffset()
    if offset:
        offset_sec = (offset.days * 24 * 3600 + offset.seconds)
        offset_hrs = offset_sec // 3600
        offset_min = offset_sec % 3600
        tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
    else:
        tz_str = 'Z'
    return dt.strftime("%Y-%m-%d %H:%M:%S") + tz_str


@contextlib.contextmanager
def timings(fmtstr, *args, **kw):
    """
    Times the running of a command, and writes a log entry afterwards.

    The log entry is passed an extra command at the beginning with the elapsed
    time in floating point seconds.
    """
    start = time.perf_counter_ns()
    yield
    end = time.perf_counter_ns()
    log.info(fmtstr, (end - start) / 1_000_000_000, *args, extra=kw)


def dump_meta(val: Any) -> Union[None, bool, int, float, str, List, Tuple, Set, Dict]:
    """
    Dump data into a dict, for use with dump_meta in to_dict methods
    """
    import jinja2

    from ..page import Page
    if val in (None, True, False) or isinstance(val, (int, float)):
        return val
    elif isinstance(val, str):
        return str(val)
    elif isinstance(val, Page):
        return f"{val.__class__.__name__}({val})"
    elif isinstance(val, dict):
        return {k: dump_meta(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple, set)):
        return [dump_meta(v) for v in val]
    elif isinstance(val, jinja2.Template):
        return f"compiled:{val.name}"
    elif hasattr(val, "to_dict"):
        return dump_meta(val.to_dict())
    else:
        return str(val)


@contextlib.contextmanager
def open_dir_fd(path, dir_fd=None):
    """
    Return a dir_fd for a directory. Supports dir_fd for opening.
    """
    res = os.open(path, os.O_RDONLY, dir_fd=dir_fd)
    try:
        yield res
    finally:
        os.close(res)


def arrange(pages: List[Page], sort: str, limit: Optional[int] = None) -> List[Page]:
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

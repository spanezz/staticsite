from __future__ import annotations

import contextlib
import datetime
import logging
import os
import time
from typing import Any, Generator, Optional, Union

import pytz

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
def timings(fmtstr: str, *args: Any, **kw: Any) -> Generator[None, None, None]:
    """
    Times the running of a command, and writes a log entry afterwards.

    The log entry is passed an extra command at the beginning with the elapsed
    time in floating point seconds.
    """
    start = time.perf_counter_ns()
    yield
    end = time.perf_counter_ns()
    log.info(fmtstr, (end - start) / 1_000_000_000, *args, extra=kw)


def dump_meta(val: Any) -> Union[None, bool, int, float, str, list[Any], tuple[Any, ...], set[Any], dict[str, Any]]:
    """
    Dump data into a dict, for use with dump_meta in to_dict methods
    """
    import jinja2

    from ..page import Page
    if val is None:
        return None
    elif isinstance(val, (bool, int, float)):
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
def open_dir_fd(path: str, dir_fd: Optional[int] = None) -> Generator[int, None, None]:
    """
    Return a dir_fd for a directory. Supports dir_fd for opening.
    """
    res = os.open(path, os.O_RDONLY, dir_fd=dir_fd)
    try:
        yield res
    finally:
        os.close(res)

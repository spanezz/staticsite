from __future__ import annotations
from typing import Union, Any, List, Tuple, Set, Dict
import contextlib
import functools
import time
import logging
import os
import pytz
import datetime

log = logging.getLogger("utils")


def format_date_rfc822(dt: datetime.datetime) -> str:
    from email.utils import formatdate
    return formatdate(dt.timestamp())


def format_date_rfc3339(dt: datetime.datetime) -> str:
    dt = dt.astimezone(pytz.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_date_w3cdtf(dt: datetime.datetime) -> str:
    offset = dt.utcoffset()
    offset_sec = (offset.days * 24 * 3600 + offset.seconds)
    offset_hrs = offset_sec // 3600
    offset_min = offset_sec % 3600
    if offset:
        tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
    else:
        tz_str = 'Z'
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + tz_str


def format_date_iso8601(dt: datetime.datetime) -> str:
    offset = dt.utcoffset()
    offset_sec = (offset.days * 24 * 3600 + offset.seconds)
    offset_hrs = offset_sec // 3600
    offset_min = offset_sec % 3600
    if offset:
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
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    log.info(fmtstr, end - start, *args, extra=kw)


def dump_meta(val: Any) -> Union[None, bool, int, float, str, List, Tuple, Set, Dict]:
    """
    Dump data into a dict, for use with dump_meta in to_dict methods
    """
    from .. import Page
    import jinja2
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


class lazy:
    """
    Mark a function as a lazy property.

    The first time the property is run, it is replaced by the value it
    computed, and turned into a normal member.
    """
    # from: https://stackoverflow.com/questions/3012421/python-memoising-deferred-lookup-property-decorator
    # see also: https://docs.python.org/3/howto/descriptor.html

    def __init__(self, fget):
        self.fget = fget
        functools.update_wrapper(self, fget)

    def __get__(self, obj, cls=None):
        if obj is None:
            return self

        value = self.fget(obj)
        setattr(obj, self.fget.__name__, value)
        return value


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

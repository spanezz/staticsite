from __future__ import annotations
from typing import Union
import re
import fnmatch
import contextlib
import functools
import time
import logging
import os
import pytz
import json
from . import yaml_codec

log = logging.getLogger("utils")

# re_term_json = re.compile(r"^}\s*$")
# re_term_yaml = re.compile(r"^---\s*$")
# re_term_toml = re.compile(r"^\+\+\+\s*$")
#
#
# def json_fenced_input(fd):
#     yield "{\n"
#     for line in fd:
#         yield line
#         if re_term_json.match(line):
#             break
#
#
# def yaml_fenced_input(fd):
#     for line in fd:
#         if re_term_yaml.match(line):
#             break
#         yield line
#
#
# def toml_fenced_input(fd):
#     for line in fd:
#         if re_term_toml.match(line):
#             break
#         yield line
#
#
# def parse_file_front_matter(fd):
#     """
#     Parse front matter from a file, leaving the file descriptor at the first
#     line past the end of the front matter, or at the end of file
#     """
#     lead = fd.readline().strip()
#     if lead == "{":
#         return "json", json.load(json_fenced_input(fd))
#
#     if lead == "+++":
#         import toml
#         return "toml", toml.load(toml_fenced_input(fd))
#
#     if lead == "---":
#         return "yaml", yaml_codec.load(yaml_fenced_input(fd))
#
#     return None, {}


def parse_front_matter(lines):
    """
    Parse lines of front matter
    """
    if not lines:
        return "toml", {}

    if lines[0] == "{":
        # JSON
        return "json", json.loads("\n".join(lines))

    if lines[0] == "+++":
        # TOML
        import toml
        return "toml", toml.loads("\n".join(lines[1:-1]))

    if lines[0] == "---":
        # YAML
        if len(lines) == 1:
            return "yaml", {}

        # Optionally remove a trailing ---
        if lines[-1] == "---":
            lines = lines[:-1]

        yaml_body = "\n".join(lines)
        return "yaml", yaml_codec.loads(yaml_body)

    return None, {}


def write_front_matter(meta, style="toml"):
    if style == "json":
        return json.dumps(meta, indent=4, sort_keys=True)
    elif style == "toml":
        import toml
        return "+++\n" + toml.dumps(meta) + "+++\n"
    elif style == "yaml":
        return yaml_codec.dumps(meta) + "---\n"
    return ""


def format_date_rfc822(dt):
    from email.utils import formatdate
    return formatdate(dt.timestamp())


def format_date_rfc3339(dt):
    dt = dt.astimezone(pytz.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_date_w3cdtf(dt):
    offset = dt.utcoffset()
    offset_sec = (offset.days * 24 * 3600 + offset.seconds)
    offset_hrs = offset_sec // 3600
    offset_min = offset_sec % 3600
    if offset:
        tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
    else:
        tz_str = 'Z'
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + tz_str


def format_date_iso8601(dt):
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


def dump_meta(val):
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

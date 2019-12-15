from __future__ import annotations
from typing import Union
import re
import fnmatch
import contextlib
import time
import logging
import io
import pytz
try:
    import ruamel.yaml
    yaml = ruamel.yaml.YAML(typ="safe", pure=True)
    yaml_load_args = {}
    yaml_dump_args = {}
    # Hack to do unsorted serialization with ruamel
    yaml_dump = ruamel.yaml.YAML(typ="rt", pure=True).dump
except ModuleNotFoundError:
    import yaml
    yaml = yaml
    yaml_load_args = {"Loader": yaml.CLoader}
    # From pyyaml 5.1, one can add sort_keys=False
    # Before that version, it seems impossible to do unsorted serialization
    # with pyyaml
    # https://stackoverflow.com/questions/16782112/can-pyyaml-dump-dict-items-in-non-alphabetical-order
    yaml_dump_args = {"Dumper": yaml.CDumper}
    yaml_dump = yaml.dump

log = logging.getLogger()


def parse_front_matter(lines):
    """
    Parse lines of front matter
    """
    if not lines:
        return "toml", {}

    if lines[0] == "{":
        # JSON
        import json
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
        return "yaml", yaml.load(yaml_body, **yaml_load_args)

    return None, {}


def write_front_matter(meta, style="toml"):
    if style == "json":
        import json
        return json.dumps(meta, indent=4, sort_keys=True)
    elif style == "toml":
        import toml
        return "+++\n" + toml.dumps(meta) + "+++\n"
    elif style == "yaml":
        # From pyyaml 5.1, one can add sort_keys=False
        # https://stackoverflow.com/questions/16782112/can-pyyaml-dump-dict-items-in-non-alphabetical-order
        with io.StringIO() as buf:
            print("---", file=buf)
            yaml_dump(meta, buf, **yaml_dump_args)
            print("---", file=buf)
            return buf.getvalue()
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
      * otherwise, it is considered a glob experssion, and fnmatch.translate()
        is used to convert it to a regular expression, then compiled
    """
    if hasattr(pattern, "match"):
        return pattern
    if pattern and (pattern[0] == '^' or pattern[-1] == '$'):
        return re.compile(pattern)
    return re.compile(fnmatch.translate(pattern))

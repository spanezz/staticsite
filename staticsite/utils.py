from __future__ import annotations
import pytz
import contextlib
import time
import logging

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
        try:
            import ruamel.yaml
            yaml = ruamel.yaml.YAML()
            load_args = {}
        except ModuleNotFoundError:
            import yaml
            yaml = yaml
            load_args = {"Loader": yaml.CLoader}
        yaml_body = "\n".join(lines[1:-1])
        return "yaml", yaml.load(yaml_body, **load_args)

    return {}


def write_front_matter(meta, style="toml"):
    if style == "json":
        import json
        return json.dumps(meta, indent=4, sort_keys=True)
    elif style == "toml":
        import toml
        return "+++\n" + toml.dumps(meta) + "+++\n"
    elif style == "yaml":
        import yaml
        return "---\n" + yaml.dump(meta) + "---\n"
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

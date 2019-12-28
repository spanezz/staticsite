from __future__ import annotations
from typing import Dict, Any, Tuple, Optional, BinaryIO
from .typing import Meta
import logging
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


def parse(lines) -> Tuple[Optional[str], Dict[str, Any]]:
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


def write(meta: Dict[str, Any], style: str = "toml") -> str:
    if style == "json":
        return json.dumps(meta, indent=4, sort_keys=True)
    elif style == "toml":
        import toml
        return "+++\n" + toml.dumps(meta) + "+++\n"
    elif style == "yaml":
        return yaml_codec.dumps(meta) + "---\n"
    return ""


def read_partial(fd: BinaryIO) -> Tuple[str, Meta]:
    """
    Parse lines front matter from a file header.

    Stop reading at the end of the front matter.

    Returns the format of the front matter read, and the byte unparsed contents
    of the front matter.
    """
    buf = bytearray()
    line = fd.readline()
    head = line.strip()
    if head == b"{":
        # JSON, end at }
        buf += line
        while True:
            line = fd.readline()
            if not line:
                raise ValueError("unterminated json front matter")
            buf += line
            if line.strip() == b"}":
                return "json", json.loads(buf)
    elif head == b"---":
        # YAML, end at ---
        buf += line
        while True:
            line = fd.readline()
            if not line or line.strip() == b"---":
                return "yaml", yaml_codec.loads(buf.decode())
            buf += line
    elif head == b"+++":
        # TOML, end at +++
        while True:
            line = fd.readline()
            if not line or line.strip() == b"+++":
                import toml
                return "toml", toml.loads(buf.decode())
            buf += line
    else:
        # No front matter found
        return None, {}

from __future__ import annotations
from typing import Dict, Any, Tuple, BinaryIO
from .typing import Meta
import logging
import json
import re
from . import yaml_codec

log = logging.getLogger("utils")


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

    Returns the format of the front matter read, and parsed front matter.
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
            if line.rstrip() == b"}":
                return "json", json.loads(buf.decode())
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


re_toml = re.compile(r"^\+\+\+[ \t]*\n(.+?)\n\+\+\+[ \t]*\n$", re.DOTALL)


def read_whole(fd: BinaryIO) -> Tuple[str, Meta]:
    """
    Parse lines front matter from a file header.

    Read the entire file

    Returns the format of the front matter read, and parsed front matter
    """
    content = fd.read().decode()
    if content.startswith("{"):
        return "json", json.loads(content)

    mo = re_toml.match(content)
    if mo:
        import toml
        return "toml", toml.loads(mo.group(1))

    return "yaml", yaml_codec.loads(content)


def read_string(content: str) -> Tuple[str, Meta]:
    """
    Parse lines front matter from a file header.

    Read data from a string.

    Returns the format of the front matter read, and parsed front matter
    """
    if content.startswith("{"):
        return "json", json.loads(content)

    mo = re_toml.match(content)
    if mo:
        import toml
        return "toml", toml.loads(mo.group(1))

    return "yaml", yaml_codec.loads(content)

from __future__ import annotations

import json
import logging
import re
from collections.abc import Generator, Iterable
from typing import IO, Any

from . import yaml_codec

log = logging.getLogger("utils")


def write(meta: dict[str, Any], style: str = "toml") -> str:
    if style == "json":
        return json.dumps(meta, indent=4, sort_keys=True)
    elif style == "toml":
        import toml

        return "+++\n" + toml.dumps(meta) + "+++\n"
    elif style == "yaml":
        return yaml_codec.dumps(meta) + "---\n"
    return ""


def read_markdown_partial(
    fd: IO[bytes],
) -> tuple[str | None, dict[str, Any], Iterable[str]]:
    """
    Parse lines front matter from a markdown file header.

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
                return (
                    "json",
                    json.loads(buf.decode()),
                    (x.rstrip().decode() for x in fd),
                )
    elif head == b"---":
        # YAML, end at ---
        buf += line
        while True:
            line = fd.readline()
            if not line or line.rstrip() == b"---":
                return (
                    "yaml",
                    yaml_codec.loads(buf.decode()),
                    (x.rstrip().decode() for x in fd),
                )
            buf += line
    elif head == b"+++":
        # TOML, end at +++
        while True:
            line = fd.readline()
            if not line or line.rstrip() == b"+++":
                import toml

                return (
                    "toml",
                    toml.loads(buf.decode()),
                    (x.rstrip().decode() for x in fd),
                )
            buf += line
    elif head.startswith(b"```"):
        # Markdown verbatim block, end at ```, format follows head
        while True:
            line = fd.readline()
            if not line or line.rstrip() == b"```":
                break
            buf += line
        if head[3:] == b"yaml":
            return (
                "yaml",
                yaml_codec.loads(buf.decode()),
                (x.rstrip().decode() for x in fd),
            )
        elif head[3:] == b"toml":
            import toml

            return "toml", toml.loads(buf.decode()), (x.rstrip().decode() for x in fd)
        elif head[3:] == b"json":
            return "json", json.loads(buf.decode()), (x.rstrip().decode() for x in fd)
        else:
            return (
                "yaml",
                yaml_codec.loads(buf.decode()),
                (x.rstrip().decode() for x in fd),
            )
    else:
        # No front matter found
        def iter_body() -> Generator[str, None, None]:
            yield line.rstrip().decode()
            for x in fd:
                yield x.rstrip().decode()

        return None, {}, iter_body()


re_toml = re.compile(r"^\+\+\+[ \t]*\n(.+?)\n\+\+\+[ \t]*\n$", re.DOTALL)


def read_whole(fd: IO[str]) -> tuple[str, dict[str, Any]]:
    """
    Parse lines front matter from a file header.

    Read the entire file

    Returns the format of the front matter read, and parsed front matter
    """
    content = fd.read()
    if content.startswith("{"):
        return "json", (val if (val := json.loads(content)) is not None else {})

    mo = re_toml.match(content)
    if mo:
        import toml

        return "toml", (val if (val := toml.loads(mo.group(1))) is not None else {})

    return "yaml", (val if (val := yaml_codec.loads(content)) is not None else {})


def read_string(content: str) -> tuple[str, dict[str, Any]]:
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

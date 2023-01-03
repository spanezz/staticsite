from __future__ import annotations

import argparse
import logging
import shlex
import subprocess
import tempfile
from typing import Any

from ..cache import DisabledCache
from ..utils import images
from ..utils import yaml_codec as yaml

from .command import Command, Fail, Success, register

log = logging.getLogger("meta")


@register
class Meta(Command):
    """
    Edit metadata for a file
    """
    def __init__(self, *args: Any, **kw: Any):
        super().__init__(*args, **kw)
        self.scanner = images.ImageScanner(DisabledCache("disabled"))

    def edit(self, fname: str) -> subprocess.CompletedProcess:
        """
        Run the editor on this file
        """
        settings_dict = self.settings.as_dict()
        cmd = [x.format(name=fname, **settings_dict) for x in self.settings.EDIT_COMMAND]
        try:
            res = subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise Fail("Editor command {} exited with error {}".format(
                " ".join(shlex.quote(x) for x in cmd), e.returncode))
        return res

    def edit_meta(self, meta: dict[str, Any]) -> dict[str, Any]:
        """
        Edit the given metadata in an editor
        """
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="wt") as fd:
            yaml.dump(meta, fd)
            fd.flush()
            self.edit(fd.name)
            with open(fd.name, "rt") as newfd:
                if not isinstance((res := yaml.load(newfd)), dict):
                    raise RuntimeError("YAML did not parse as a dict")
                return res

    def save_changes(self, old_meta: dict[str, Any], new_meta: dict[str, Any]) -> None:
        # Compute and store the changes
        changed = {}
        removed = []
        for key, orig in old_meta.items():
            if key not in new_meta:
                log.info("%s: removed %s", self.args.file, key)
                removed.append(key)
            elif new_meta[key] != orig:
                log.info("%s: updated %s=%r", self.args.file, key, new_meta[key])
                changed[key] = new_meta[key]

        for key in new_meta.keys() - old_meta.keys():
            log.info("%s: added %s=%r", self.args.file, key, new_meta[key])
            changed[key] = new_meta[key]

        if not changed and not removed:
            raise Success()

        if not self.scanner.edit_meta_exiftool(self.args.file, changed, removed):
            raise Fail("Failed to store metadatä changes")

    def run(self) -> None:
        # TODO: Build a Site if possible
        # TODO: or load settings from a settings.py if one can be found in reasonable places

        # Read file metadata
        meta = self.scanner.scan_file(self.args.file)

        # Filter the keys that we don't need to edit
        meta.pop("width", None)
        meta.pop("height", None)
        meta.pop("lat", None)
        meta.pop("lon", None)

        # Set the keys that are relevant and might not be there to default values
        meta.setdefault("title", "")
        meta.setdefault("author", "")
        meta.setdefault("copyright", "")

        # Edit the metadata
        new_meta = self.edit_meta(meta)

        self.save_changes(meta, new_meta)

    @classmethod
    def add_subparser(cls, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = super().add_subparser(subparsers)
        parser.add_argument("file", help="edit the metadata of this file")
        return parser

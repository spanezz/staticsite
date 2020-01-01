import subprocess
from .command import Command, Fail, Success
from staticsite.utils import images
from staticsite.cache import DisabledCache
from staticsite.utils import yaml_codec as yaml
import shlex
import tempfile
import logging

log = logging.getLogger("meta")


class Meta(Command):
    """
    Edit metadata for a file
    """
    def edit(self, fname):
        settings_dict = self.settings.as_dict()
        cmd = [x.format(name=fname, **settings_dict) for x in self.settings.EDIT_COMMAND]
        try:
            res = subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise Fail("Editor command {} exited with error {}".format(
                " ".join(shlex.quote(x) for x in cmd), e.returncode))
        return res

    def run(self):
        # TODO: Build a Site if possible
        # TODO: or load settings from a settings.py if one can be found in reasonable places
        scanner = images.ImageScanner(DisabledCache())
        meta = scanner.scan_file(self.args.file)
        with tempfile.NamedTemporaryFile(suffix=".yaml") as fd:
            yaml.dump(meta, fd)
            fd.flush()
            # TODO: filter the keys that we don't need to edit, like width and height
            # TODO: setdefault the keys that are relevant and might not be there
            self.edit(fd.name)
            with open(fd.name, "rt") as newfd:
                new_meta = yaml.load(newfd)

        # TODO: set in file
        changed = {}
        removed = []
        for key, orig in meta.items():
            if key not in new_meta:
                log.info("%s: removed %s", self.args.file, key)
                removed.append(key)
            elif new_meta[key] != orig:
                log.info("%s: updated %s=%r", self.args.file, key, new_meta[key])
                changed[key] = new_meta[key]

        for key in new_meta.keys() - meta.keys():
            log.info("%s: added %s=%r", self.args.file, key, new_meta[key])
            changed[key] = new_meta[key]

        if not changed and not removed:
            raise Success()

        if not scanner.edit_meta_exiftool(self.args.file, changed, removed):
            raise Fail("Failed to store metadatä changes")

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("file", help="edit the metadata of this file")
        return parser

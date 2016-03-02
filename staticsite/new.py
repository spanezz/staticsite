# coding: utf-8

import os
import shutil
import json
import datetime
import time
import subprocess
import shlex
from collections import OrderedDict
from .commands import SiteCommand, CmdlineError
from .core import settings
import logging

log = logging.getLogger()

class New(SiteCommand):
    "create a new page"

    def run(self):
        site = self.load_site()

        archetype = site.load_archetype(self.args.archetype)
        if archetype is None:
            raise CmdlineError("archetype {} not found".format(self.args.archetype))
        log.info("Using archetype %s", archetype.relpath)

        title = self.args.title
        if title is None:
            title = input("Please enter the post title: ")

        if title is None:
            slug = None
        else:
            slug = site.slugify(title)

        meta_style, meta, body = archetype.render(slug=slug, title=title)

        relpath = meta.pop("path", None)
        if relpath is None:
            raise CmdlineError("archetype {} does not contain `path` in its front matter".format(archetype.relpath))

        abspath = os.path.join(site.site_root, relpath)

        if self.args.overwrite or not os.path.exists(abspath):
            from .utils import write_front_matter
            front_matter = write_front_matter(meta, meta_style)

            os.makedirs(os.path.dirname(abspath), exist_ok=True)

            with open(abspath, "wt") as out:
                out.write(front_matter)
                print(file=out)
                for line in body:
                    print(line, file=out)
        else:
            log.info("%s already exists: reusing it", abspath)

        if not self.args.noedit:
            settings_dict = settings.as_dict()
            cmd = [x.format(name=abspath, slug=slug, **settings_dict) for x in settings.EDIT_COMMAND]
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                log.warn("Editor command %s exited with error %d", " ".join(shlex.quote(x) for x in cmd), e.returncode)
                return e.returncode
        print(abspath)

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("-a", "--archetype", default="default", help="page archetype")
        parser.add_argument("-t", "--title", help="page title")
        parser.add_argument("-n", "--noedit", help="do not run an editor, only output the file name of the new post")
        parser.add_argument("--overwrite", action="store_true", help="if a post already exists, overwrite it instead of reusing it")
        return parser

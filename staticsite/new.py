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
from .archetypes import Archetypes
import logging

log = logging.getLogger()

class LazyTitle:
    """
    Wrapper for the value of a post title.

    If no value has been provided and one is requested by the template, ask the
    user for one.
    """
    def __init__(self, title=None):
        self.title = title

    def __str__(self):
        if self.title is None:
            self.title = input("Please enter the post title: ")
        return self.title


class LazySlug:
    """
    Generate a slug from the value of LazyTitle
    """
    def __init__(self, site, lazy_title):
        self.site = site
        self.lazy_title = lazy_title

    def __str__(self):
        return self.site.slugify(str(self.lazy_title))


class New(SiteCommand):
    "create a new page"

    def run(self):
        site = self.load_site()

        archetypes = Archetypes(site, os.path.join(self.root, "archetypes"))

        archetype = archetypes.find(self.args.archetype)
        if archetype is None:
            raise CmdlineError("archetype {} not found".format(self.args.archetype))
        log.info("Using archetype %s", archetype.relpath)

        title = LazyTitle(self.args.title)
        slug = LazySlug(site, title)
        meta_style, meta, body = archetype.render(slug=slug, title=title)

        relpath = meta.pop("path", None)
        if relpath is None:
            raise CmdlineError("archetype {} does not contain `path` in its front matter".format(archetype.relpath))

        abspath = os.path.join(self.content_root, relpath)

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
            settings_dict = site.settings.as_dict()
            cmd = [x.format(name=abspath, slug=slug, **settings_dict) for x in site.settings.EDIT_COMMAND]
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
        parser.add_argument("-n", "--noedit", action="store_true", help="do not run an editor, only output the file name of the new post")
        parser.add_argument("--overwrite", action="store_true", help="if a post already exists, overwrite it instead of reusing it")
        return parser

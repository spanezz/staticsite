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

        title = self.args.title
        if title is None:
            title = input("Please enter the post title: ")

        if title is None:
            slug = None
        else:
            slug = site.slugify(title)

        settings_dict = settings.as_dict()

        relpath = settings.NEW_PAGE.format(
            slug=slug,
            time=site.generation_time,
            **settings_dict,
        )

        abspath = os.path.join(site.site_root, relpath)

        if not os.path.exists(abspath):
            # Use an OrderedDict in hope that toml and yaml will not serialize
            # front matter keys in random order. Will not, that is, when we will
            # have more than one.
            meta = OrderedDict()
            from .utils import format_date_iso8601
            meta["date"] = format_date_iso8601(site.generation_time)
            from .utils import write_front_matter
            front_matter = write_front_matter(meta)

            os.makedirs(os.path.dirname(abspath), exist_ok=True)

            with open(abspath, "wt") as out:
                out.write(front_matter)
                print(file=out)
                print("# {title}".format(title=title), file=out)

        if self.args.noedit:
            print(abspath)
        else:
            cmd = [x.format(name=abspath, slug=slug, **settings_dict) for x in settings.EDIT_COMMAND]
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                log.warn("Editor command %s exited with error %d", " ".join(shlex.quote(x) for x in cmd), e.returncode)
                return e.returncode

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("-t", "--title", help="page title")
        parser.add_argument("-n", "--noedit", help="do not run an editor, only output the file name of the new post")
        return parser

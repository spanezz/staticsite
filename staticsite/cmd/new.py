from __future__ import annotations

import argparse
import logging
import os
import shlex
import subprocess
from typing import TYPE_CHECKING, Optional

from .command import Fail, SiteCommand, register

if TYPE_CHECKING:
    from ..site import Site

log = logging.getLogger("new")


class LazyTitle:
    """
    Wrapper for the value of a post title.

    If no value has been provided and one is requested by the template, ask the
    user for one.
    """
    def __init__(self, title: Optional[str] = None) -> None:
        self.title = title

    def __str__(self) -> str:
        if self.title is None:
            self.title = input("Please enter the post title: ")
        return self.title

    def __len__(self) -> int:
        return len(str(self))


class LazySlug:
    """
    Generate a slug from the value of LazyTitle
    """
    def __init__(self, site: Site, lazy_title: LazyTitle):
        self.site = site
        self.lazy_title = lazy_title

    def __str__(self) -> str:
        return self.site.slugify(str(self.lazy_title))


@register
class New(SiteCommand):
    "create a new page"

    def run(self) -> Optional[int]:
        site = self.load_site()

        archetype = site.archetypes.find(self.args.archetype)
        if archetype is None:
            raise Fail("archetype {} not found".format(self.args.archetype))
        log.info("Using archetype %s", archetype.relpath)

        title = LazyTitle(self.args.title)
        slug = LazySlug(site, title)
        meta, body = archetype.render(slug=slug, title=title)

        relpath = meta.get("path", None)
        if relpath is None:
            raise Fail("archetype {} does not contain `path` in its front matter".format(archetype.relpath))

        if site.settings.PROJECT_ROOT is None:
            raise Fail("PROJECT_ROOT is empty")
        if site.settings.CONTENT is None:
            raise Fail("CONTENT is empty")

        content_root = os.path.join(site.settings.PROJECT_ROOT, site.settings.CONTENT)
        abspath = os.path.join(content_root, relpath)
        if self.args.overwrite or not os.path.exists(abspath):
            os.makedirs(os.path.dirname(abspath), exist_ok=True)
            with open(abspath, "wt") as out:
                out.write(body)
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
        return None

    @classmethod
    def add_subparser(cls, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = super().add_subparser(subparsers)
        parser.add_argument("-a", "--archetype", default="default", help="page archetype")
        parser.add_argument("-t", "--title", help="page title")
        parser.add_argument("-n", "--noedit", action="store_true",
                            help="do not run an editor, only output the file name of the new post")
        parser.add_argument("--overwrite", action="store_true",
                            help="if a post already exists, overwrite it instead of reusing it")
        return parser

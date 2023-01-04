from __future__ import annotations

import argparse
import logging
import os
from typing import Any, Type

from staticsite.settings import Settings
from staticsite.site import Site
from staticsite.utils import timings

from . import cli

Fail = cli.Fail
Success = cli.Success

log = logging.getLogger("command")

COMMANDS: list[Type["Command"]] = []


def register(c: Type["Command"]) -> Type["Command"]:
    COMMANDS.append(c)
    return c


class Command(cli.Command):
    def __init__(self, args: argparse.Namespace):
        super().__init__(args)
        self.settings = Settings()
        self.settings.BUILD_COMMAND = self.NAME

    def load_site(self) -> Site:
        # Instantiate site
        site = Site(settings=self.settings)
        with timings("Loaded site in %fs"):
            site.load()

        # If --debug=list was requested
        if self.args.debug == "list":
            for name in sorted(logging.root.manager.loggerDict):
                print(name)
            raise Success()
        return site

# TODO: enable debugging for specific loggers only
#         parser.add_argument("--debug", nargs="?", action="store", const=True, help="verbose output")


class SiteCommand(Command):
    def __init__(self, *args: Any, **kw: Any):
        super().__init__(*args, **kw)

        # Look for extra settings
        settings_files = ['settings.py', '.staticsite.py']
        if self.args.project:
            if os.path.isfile(self.args.project):
                # If a project file is mentioned, take its directory as default
                # project root
                settings_file = os.path.abspath(self.args.project)
                settings_dir, settings_file = os.path.split(settings_file)
                if not self.args.project.endswith(".py"):
                    log.warning("%s: project settings does not end in `.py`: contents ignored", settings_file)
                else:
                    settings_files = [settings_file]
            else:
                # If a project directory is mentioned, take it as default
                # project root
                settings_dir = os.path.abspath(self.args.project)
        else:
            settings_dir = os.getcwd()

        # Load the first settings file found (if any)
        for relpath in settings_files:
            abspath = os.path.join(settings_dir, relpath)
            if os.path.isfile(abspath):
                log.info("%s: loading settings", abspath)
                self.settings.load(abspath)
                break

        # Set default project root if undefined
        if self.settings.PROJECT_ROOT is None:
            self.settings.PROJECT_ROOT = settings_dir

        # Command line overrides for settings
        if self.args.theme:
            self.settings.THEME = (os.path.abspath(self.args.theme),)
        if self.args.content:
            self.settings.CONTENT = os.path.abspath(self.args.content)
        if self.args.archetypes:
            self.settings.ARCHETYPES = os.path.abspath(self.args.archetypes)
        if self.args.output:
            self.settings.OUTPUT = os.path.abspath(self.args.output)
        if self.args.draft:
            self.settings.DRAFT_MODE = True

    @classmethod
    def add_subparser(cls, subparsers: "argparse._SubParsersAction[Any]") -> argparse.ArgumentParser:
        parser = super().add_subparser(subparsers)

        parser.add_argument("project", nargs="?",
                            help="project directory or .py configuration file (default: the current directory)")
        parser.add_argument("--theme", help="theme directory location. Overrides settings.THEME")
        parser.add_argument("--content", help="content directory location. Overrides settings.CONTENT")
        parser.add_argument("--archetypes", help="archetypes directory location. Override settings.ARCHETYPES")
        parser.add_argument("-o", "--output", help="output directory location. Override settings.OUTPUT")
        parser.add_argument("--draft", action="store_true", help="do not ignore pages with date in the future")

        return parser

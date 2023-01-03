from __future__ import annotations

import argparse
import logging
import sys
from typing import TYPE_CHECKING, Any

from .command import SiteCommand, register
from . import cli

if TYPE_CHECKING:
    import staticsite.site

log = logging.getLogger("site")


class FeatureCommand(cli.Command):
    """
    Command parser that can be run after the site is loaded
    """
    def __init__(self, site: staticsite.site.Site, args: argparse.Namespace):
        # Intentionally do not call super().__init__, to avoid reinitializing logs
        self.site = site
        self.args = args


class List(FeatureCommand):
    "list available features"

    def run(self) -> None:
        for feature in self.site.features.ordered():
            print("{} - {}".format(feature.name, feature.get_short_description()))


@register
class Site(SiteCommand):
    "run feature-specifc commands"

    @classmethod
    def add_subparser(cls, subparsers: "argparse._SubParsersAction[Any]") -> argparse.ArgumentParser:
        parser = super().add_subparser(subparsers)
        parser.add_argument("--cmd", nargs=argparse.REMAINDER, help="site-specific command (try 'help')")
        return parser

    def run(self) -> None:
        site = self.load_site()

        # Build the site-specific command line parser
        parser = argparse.ArgumentParser(description="Site-specific commands.")
        subparsers = parser.add_subparsers(help="sub-command help", dest="command")

        List.add_subparser(subparsers)

        for feature in site.features.ordered():
            feature.add_site_commands(subparsers)

        args = parser.parse_args(self.args.cmd)

        if args.command is None:
            parser.print_help()
        else:
            handler = args.handler(site, args)
            res = handler.run()
            if res is not None:
                sys.exit(res)

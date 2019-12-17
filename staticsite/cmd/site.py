from .command import SiteCommand
import argparse
import sys
import logging

log = logging.getLogger("site")


class FeatureCommand:
    # Command name (as used in command line)
    # Defaults to the lowercased class name
    NAME = None

    # Command description (as used in command line help)
    # Defaults to the strip()ped class docstring.
    DESC = None

    def __init__(self, site, args):
        self.site = site
        self.args = args

    @classmethod
    def make_subparser(cls, subparsers):
        name = cls.NAME
        if name is None:
            name = cls.__name__.lower()

        desc = cls.DESC
        if desc is None:
            desc = cls.__doc__.strip()

        parser = subparsers.add_parser(name, help=desc)
        parser.set_defaults(handler=cls)
        return parser


class List(FeatureCommand):
    "list available features"
    def run(self):
        for feature in self.site.features.ordered():
            print("{} - {}".format(feature.name, feature.get_short_description()))


class Site(SiteCommand):
    "run feature-specifc commands"

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("--cmd", nargs=argparse.REMAINDER, help="site-specific command (try 'help')")
        return parser

    def run(self):
        site = self.load_site()

        # Build the site-specific command line parser
        parser = argparse.ArgumentParser(description="Site-specific commands.")
        subparsers = parser.add_subparsers(help="sub-command help", dest="command")

        List.make_subparser(subparsers)

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

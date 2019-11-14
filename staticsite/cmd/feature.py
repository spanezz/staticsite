# import argparse
from .command import SiteCommand
import logging

log = logging.getLogger()


# class SiteSpecificCommand:
#     @classmethod
#     def make_subparser(cls, subparsers):
#         name = cls.NAME
#         if name is None:
#             name = cls.__name__.lower()
#
#         desc = cls.DESC
#         if desc is None:
#             desc = cls.__doc__.strip()
#
#         parser = subparsers.add_parser(name, help=desc)
#         parser.set_defaults(handler=cls)
#         return parser
#
#
# class Help:
#     @classmethod
#     def make_subparser(cls, subparsers):
#         parser = super().make_subparser(subparsers)
#         parser.add_argument("cmd", nargs="?", help="print help on this specific command")
#         return parser


class Feature(SiteCommand):
    "run feature-specifc commands"

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("name", nargs="?", help="feature name")
        parser.add_argument("--list", action="store_true", help="list all features")
        return parser

    def run(self):
        site = self.load_site()

        if self.args.list:
            for feature in site.features.ordered():
                print("{} - {}".format(feature.name, feature.get_short_description()))
        else:
            raise NotImplementedError("this is an entry point for allowing features to provide their own site specific commands")
            # print(self.args)

#        parser = argparse.ArgumentParser(description="Site commands.")
#        subparsers = parser.add_subparsers(help="site commands help", dest="command")
#
#        parser = subparsers.add_parser("help", help="print help on site commands")
#        ))parser.add_argument("cmd", nargs="?", help="print help on this specific command")
#        site_args = parser.parse_args(self.args.cmd)
#        
#        print(self.args)
#        parser.set_defaults(handler=cls)
#        print(site_args)

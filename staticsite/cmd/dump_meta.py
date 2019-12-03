from .command import SiteCommand
import logging

log = logging.getLogger()


class DumpMeta(SiteCommand):
    "Dump the metadata of each page in the site"

    NAME = "dump_meta"

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("--repr", action="store_true",
                            help="show repr() version of metadata values")
        return parser

    def run(self):
        site = self.load_site()
        show_repr = self.args.repr
        for relpath, page in sorted(site.pages.items()):
            print(f"/{relpath}:")
            for k, v in sorted(page.meta.items()):
                if show_repr:
                    print(f" {k}: {v!r}")
                else:
                    print(f" {k}: {v}")

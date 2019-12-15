from .command import SiteCommand
from staticsite.utils import write_front_matter, compile_page_match
import sys
import logging

log = logging.getLogger()


class DumpMeta(SiteCommand):
    "Dump the metadata of each page in the site"

    NAME = "dump_meta"

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("-f", "--format", action="store", default="yaml",
                            help="format to use for output")
        parser.add_argument("-p", "--pages", nargs="+", default=(),
                            help="globs or regexps matching pages to show")
        return parser

    def run(self):
        site = self.load_site()
        filters = [compile_page_match(f) for f in self.args.pages]
        res = {}
        # show_repr = self.args.repr
        for relpath, page in sorted(site.pages.items()):
            if filters and not any(f.match(relpath) for f in filters):
                continue
            res[f"/{relpath}"] = page.to_dict()
        sys.stdout.write(write_front_matter(res, self.args.format))

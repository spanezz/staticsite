from __future__ import annotations
from .command import SiteCommand
from staticsite.utils import front_matter
from staticsite.page_filter import compile_page_match
import sys
import logging

log = logging.getLogger("dump_meta")


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
        parser.add_argument("--doc", action="store_true",
                            help="print documentation for all known metadata")
        return parser

    def run(self):
        site = self.load_site()
        if self.args.doc:
            print("""# Common page metadata

This is a list of metadata elements that have special meaning in this site.

You can use `ssite dump_meta` to see all the content and metadata that pages
make available to templates via the `page` variable.""")
            for metadata in site.metadata.values():
                print()
                print(f"### {metadata.name}")
                print()
                if metadata.inherited:
                    print("*Inherited from directory indices.*")
                    print()
                if metadata.template_for:
                    print(f"*Template version of `{metadata.template_for}`.*")
                    print()
                print(metadata.doc)
        else:
            filters = [compile_page_match(f) for f in self.args.pages]
            res = {}
            # show_repr = self.args.repr
            for relpath, page in sorted(site.pages.items()):
                if filters and not any(f.match(relpath) for f in filters):
                    continue
                res[f"/{relpath}"] = page.to_dict()
            sys.stdout.write(front_matter.write(res, self.args.format))

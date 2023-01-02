from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .command import SiteCommand, Fail

if TYPE_CHECKING:
    from ..site import Site

log = logging.getLogger("dump")


class Dump(SiteCommand):
    "Dump information about a site"

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--fstree", action="store_true",
                           help="dump information about the scanned directory trees")
        group.add_argument("--nodes", action="store_true",
                           help="dump information about the built site layout")
        group.add_argument("--changes", action="store_true",
                           help="dump information about pages that changed")
        group.add_argument("--reference-documentation", action="store", nargs="?",
                           const="doc/reference", metavar="destdir",
                           help="regenerate reference documentation")
        return parser

    def dump_fstree(self, site: Site) -> None:
        for name, fstree in site.fstrees.items():
            print(f"# {name}")
            fstree.print()

    def dump_nodes(self, site: Site) -> None:
        site.root.print()

    def dump_changes(self, site: Site) -> None:
        for page in site.iter_pages():
            change = page.change_extent
            if change > 0:
                print(f"{page!r} {change}")

    def run(self) -> None:
        site = self.load_site()
        if self.args.fstree:
            self.dump_fstree(site)
        elif self.args.nodes:
            self.dump_nodes(site)
        elif self.args.changes:
            self.dump_changes(site)
        elif self.args.reference_documentation:
            from ..autodoc import Autodoc
            autodoc = Autodoc(site, self.args.reference_documentation)
            autodoc.generate()
        else:
            raise Fail("I don't know what to do")

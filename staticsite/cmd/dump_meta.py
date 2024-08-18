from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from staticsite.page_filter import compile_page_match
from staticsite.utils import front_matter

from .command import SiteCommand, register

log = logging.getLogger("dump_meta")


@register
class DumpMeta(SiteCommand):
    "Dump the metadata of each page in the site"

    NAME = "dump_meta"

    @classmethod
    def add_subparser(
        cls, subparsers: argparse._SubParsersAction[Any]
    ) -> argparse.ArgumentParser:
        parser = super().add_subparser(subparsers)
        parser.add_argument(
            "-f",
            "--format",
            action="store",
            default="yaml",
            help="format to use for output",
        )
        parser.add_argument(
            "-p",
            "--pages",
            nargs="+",
            default=(),
            help="globs or regexps matching pages to show",
        )
        return parser

    def run(self) -> None:
        site = self.load_site()
        filters = [compile_page_match(f) for f in self.args.pages]
        res = {}
        # show_repr = self.args.repr
        for site_path, page in sorted((p.site_path, p) for p in site.iter_pages()):
            if filters and not any(f.match(site_path) for f in filters):
                continue
            res[site_path] = page.to_dict()
        sys.stdout.write(front_matter.write(res, self.args.format))

from __future__ import annotations

import argparse
import logging
import shlex
import subprocess
from typing import TYPE_CHECKING, Any, cast

from staticsite.page_filter import PageFilter

from ..page import SourcePage
from .command import Fail, SiteCommand, register

if TYPE_CHECKING:
    from staticsite.features.taxonomy import TaxonomyFeature


log = logging.getLogger("edit")


@register
class Edit(SiteCommand):
    "edit an existing page. Bare keywords match titles and file names, '+tag' matches tags"

    MENU_SIZE = 5

    def select_page_menu(self, pages: list[SourcePage]) -> SourcePage | None:
        """
        Prompt the user to select a page from `pages`.

        Returns None of the user chooses to give up insteaad.
        """
        first = 0

        while True:
            pagination = len(pages) > self.MENU_SIZE

            if pagination:
                print(
                    "{count} pages found, showing {first}-{last}:".format(
                        first=first + 1,
                        last=min(first + self.MENU_SIZE, len(pages)),
                        count=len(pages),
                    )
                )
                prompt = (
                    "Please choose which page to edit"
                    " (number, or p for previous page, n for next page, q to quit): "
                )
            else:
                print(f"{len(pages)} matching pages found:")
                prompt = "Please choose which page to edit (number, or q to quit): "
            print()

            for idx, page in enumerate(
                pages[first : first + self.MENU_SIZE], first + 1
            ):
                print(
                    "{idx}: {date} {relpath} {title}".format(
                        idx=idx,
                        date=page.meta["date"].strftime("%Y-%m-%d"),
                        relpath=page.src.relpath,
                        title=page.meta.get("title", "{no title}"),
                    )
                )
            print()

            selection = input(prompt).strip().lower()
            if selection == "q":
                return None
            elif pagination and selection == "p":
                first = max(0, first - self.MENU_SIZE)
                continue
            elif pagination and selection == "n" or selection == "":
                first = min(
                    first + self.MENU_SIZE,
                    self.MENU_SIZE * (len(pages) // self.MENU_SIZE),
                )
                continue

            if selection.isdigit():
                idx = int(selection)
                if idx < 1 or idx > len(pages):
                    print(f"{idx} does not match any page")
                else:
                    return pages[idx - 1]

    def run(self) -> int | None:
        site = self.load_site()

        filter_args: dict[str, Any] = {
            "sort": "-date",
        }

        # Filter by taxonomy
        taxonomies: TaxonomyFeature = cast("TaxonomyFeature", site.features["taxonomy"])
        args = []
        for arg in self.args.match:
            if arg.startswith("+"):
                filter_args.setdefault("tags", []).append(arg[1:])
            else:
                for name in taxonomies.taxonomies.keys():
                    if arg.startswith(f"{name}:"):
                        filter_args.setdefault("tags", []).append(arg[len(name) + 1 :])
                        break
                else:
                    args.append(arg)

        def match_page(page: SourcePage) -> bool:
            for m in args:
                if (
                    m.lower() not in page.meta.get("title", "").lower()
                    and m.lower() not in page.src.relpath.lower()
                ):
                    return False
            return True

        # Build a list of all findable pages, present on disk, sorted with the newest first
        f = PageFilter(site, **filter_args)
        pages = [
            page
            for page in f.filter()
            if isinstance(page, SourcePage) and match_page(page)
        ]

        if len(pages) == 0:
            raise Fail(
                "No page found matching {}".format(
                    " ".join(shlex.quote(x) for x in self.args.match)
                )
            )

        page: SourcePage | None
        if len(pages) == 1:
            page = pages[0]
        else:
            page = self.select_page_menu(pages)

        if page is None:
            return None

        abspath = page.src.abspath

        if not self.args.noedit:
            settings_dict = site.settings.as_dict()
            cmd = [
                x.format(name=abspath, **settings_dict)
                for x in site.settings.EDIT_COMMAND
            ]
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                log.warning(
                    "Editor command %s exited with error %d",
                    " ".join(shlex.quote(x) for x in cmd),
                    e.returncode,
                )
                return e.returncode
        print(abspath)
        return None

    @classmethod
    def add_subparser(
        cls, subparsers: argparse._SubParsersAction[Any]
    ) -> argparse.ArgumentParser:
        parser = super().add_subparser(subparsers)
        parser.add_argument(
            "match", nargs="*", help="keywords used to look for the page to edit"
        )
        parser.add_argument(
            "-n",
            "--noedit",
            action="store_true",
            help="do not run an editor, only output the file name of the new post",
        )
        return parser

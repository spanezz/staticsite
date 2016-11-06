# coding: utf-8

import os
import shutil
import json
import datetime
import time
import subprocess
import shlex
from collections import OrderedDict
from .commands import SiteCommand, CmdlineError
import logging

log = logging.getLogger()

class Edit(SiteCommand):
    "edit an existing page. Bare keywords match titles and file names, '+tag' matches tags"

    MENU_SIZE = 5

    def match_page(self, page):
        for m in self.args.match:
            if m.startswith("+"):
                tags = page.meta.get("tags", ())
                if m[1:] not in tags:
                    return False
            elif (m.lower() not in page.meta.get("title", "").lower()
                  and m.lower() not in page.src_relpath.lower()):
                return False
        return True

    def select_page_menu(self, pages):
        """
        Prompt the user to select a page from `pages`.

        Returns None of the user chooses to give up insteaad.
        """
        first = 0

        while True:
            pagination = len(pages) > self.MENU_SIZE

            if pagination:
                print("{count} pages found, showing {first}-{last}:".format(
                    first=first + 1,
                    last=min(first + self.MENU_SIZE, len(pages)),
                    count=len(pages)))
                prompt = "Please choose which page to edit (number, or p for previous page, n for next page, q to quit): "
            else:
                print("{count} matching pages found:".format(count=len(pages)))
                prompt = "Please choose which page to edit (number, or q to quit): "
            print()

            for idx, page in enumerate(pages[first:first + self.MENU_SIZE], first + 1):
                print("{idx}: {date} {relpath} {title}".format(
                    idx=idx,
                    date=page.meta["date"].strftime("%Y-%m-%d"),
                    relpath=page.src_relpath,
                    title=page.meta.get("title", "{no title}")))
            print()

            selection = input(prompt).strip().lower()
            if selection == "q":
                return None
            elif pagination and selection == "p":
                first = max(0, first - self.MENU_SIZE)
                continue
            elif pagination and selection == "n":
                first = min(first + self.MENU_SIZE, self.MENU_SIZE * (len(pages) // self.MENU_SIZE))
                continue

            if selection.isdigit():
                idx = int(selection)
                if idx < 1 or idx > len(pages):
                    print("{idx} does not match any page".format(idx=idx))
                else:
                    return pages[idx - 1]

    def run(self):
        site = self.load_site()

        # Build a list of all findable pages sorted with the newest first
        pages = [p for p in site.pages.values() if p.FINDABLE]
        pages.sort(key=lambda x:x.meta["date"], reverse=True)

        selected = []
        for page in pages:
            if not self.match_page(page): continue
            selected.append(page)

        if len(selected) == 0:
            raise CmdlineError("No page found matching {}".format(" ".join(shlex.quote(x) for x in self.args.match)))

        if len(selected) == 1:
            page = selected[0]
        else:
            page = self.select_page_menu(selected)

        if page is None:
            return

        abspath = page.src_abspath

        if not self.args.noedit:
            settings_dict = site.settings.as_dict()
            cmd = [x.format(name=abspath, **settings_dict) for x in site.settings.EDIT_COMMAND]
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                log.warn("Editor command %s exited with error %d", " ".join(shlex.quote(x) for x in cmd), e.returncode)
                return e.returncode
        print(abspath)

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("match", nargs="*", help="keywords used to look for the page to edit")
        parser.add_argument("-n", "--noedit", action="store_true", help="do not run an editor, only output the file name of the new post")
        return parser

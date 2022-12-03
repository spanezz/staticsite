import subprocess
import shlex
from .command import SiteCommand, Fail
from staticsite.page_filter import PageFilter
import logging

log = logging.getLogger("edit")


class Edit(SiteCommand):
    "edit an existing page. Bare keywords match titles and file names, '+tag' matches tags"

    MENU_SIZE = 5

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
                prompt = ("Please choose which page to edit"
                          " (number, or p for previous page, n for next page, q to quit): ")
            else:
                print("{count} matching pages found:".format(count=len(pages)))
                prompt = "Please choose which page to edit (number, or q to quit): "
            print()

            for idx, page in enumerate(pages[first:first + self.MENU_SIZE], first + 1):
                print("{idx}: {date} {relpath} {title}".format(
                    idx=idx,
                    date=page.meta["date"].strftime("%Y-%m-%d"),
                    relpath=page.src.relpath,
                    title=page.meta.get("title", "{no title}")))
            print()

            selection = input(prompt).strip().lower()
            if selection == "q":
                return None
            elif pagination and selection == "p":
                first = max(0, first - self.MENU_SIZE)
                continue
            elif pagination and selection == "n" or selection == "":
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

        filter_args = {
            "sort": "-date",
        }

        # Filter by taxonomy
        taxonomies = site.features["taxonomy"]
        args = []
        for arg in self.args.match:
            if arg.startswith("+"):
                filter_args.setdefault("tags", []).append(arg[1:])
            else:
                for name in taxonomies.taxonomies.keys():
                    if arg.startswith(f"{name}:"):
                        filter_args.setdefault("tags", []).append(arg[len(name) + 1:])
                        break
                else:
                    args.append(arg)

        def match_page(page):
            for m in args:
                if (m.lower() not in page.meta.get("title", "").lower()
                        and m.lower() not in page.src.relpath.lower()):
                    return False
            return True

        # Build a list of all findable pages, present on disk, sorted with the newest first
        f = PageFilter(site, **filter_args)
        pages = [page for page in f.filter(site.iter_pages())
                 if page.src.stat is not None and match_page(page)]

        if len(pages) == 0:
            raise Fail("No page found matching {}".format(" ".join(shlex.quote(x) for x in self.args.match)))

        if len(pages) == 1:
            page = pages[0]
        else:
            page = self.select_page_menu(pages)

        if page is None:
            return

        abspath = page.src.abspath

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
        parser.add_argument("-n", "--noedit", action="store_true",
                            help="do not run an editor, only output the file name of the new post")
        return parser

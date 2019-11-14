from staticsite.page import Page
from staticsite.rendered import RenderedString
from staticsite.feature import Feature
from collections import defaultdict
import os
import logging

log = logging.getLogger()


class DirPages(Feature):
    """
    Build indices of directory contents.

    When a directory has no index page but contains pages, this will generate
    the index page listing all pages in the directory.
    """
    RUN_AFTER = ["taxonomies"]

    def finalize(self):
        by_dir = defaultdict(list)
        for page in self.site.pages.values():
            # Harvest content for directory indices
            if page.FINDABLE and page.src_relpath:
                dir_relpath = os.path.dirname(page.src_relpath)
                by_dir[dir_relpath].append(page)
                while dir_relpath:
                    dir_relpath = os.path.dirname(dir_relpath)
                    # Do a lookup to make sure an entry exists for this
                    # directory level, even though without pages
                    by_dir[dir_relpath]

        # Build directory indices
        dir_pages = []
        for relpath, pages in by_dir.items():
            # We only build indices where there is not already a page
            if relpath in self.site.pages:
                continue
            page = DirPage(self.site, relpath, pages)
            dir_pages.append(page)
            self.site.pages[relpath] = page

        # Add directory indices to their parent directory indices
        for page in dir_pages:
            page.attach_to_parent()

        for page in dir_pages:
            page.finalize()


class DirPage(Page):
    """
    A directory index
    """
    TYPE = "dir"
    ANALYZE_PASS = 3
    RENDER_PREFERRED_ORDER = 2

    def __init__(self, site, relpath, pages):
        super().__init__(
            site=site,
            root_abspath=None,
            src_relpath=relpath,
            src_linkpath=relpath,
            dst_relpath=os.path.join(relpath, "index.html"),
            dst_link=os.path.join(site.settings.SITE_ROOT, relpath))

        self.pages = list(pages)
        self.subdirs = []

    def attach_to_parent(self):
        if not self.src_relpath:
            return
        parent_relpath = os.path.dirname(self.src_relpath)
        parent = self.site.pages[parent_relpath]
        if parent.TYPE != "dir":
            return
        if self in parent.subdirs:
            return
        parent.subdirs.append(self)
        parent.attach_to_parent()

    @property
    def src_abspath(self):
        return None

    def get_date(self):
        # Sort by decreasing date
        res = self.meta.get("date", None)
        if res is None:
            self.pages.sort(key=lambda x: x.meta["date"], reverse=True)
            if self.pages:
                dates = [self.pages[0].meta["date"]]
            else:
                dates = []
            dates.extend(d.get_date() for d in self.subdirs)
            if not dates:
                self.meta["date"] = res = None
            else:
                self.meta["date"] = res = max(dates)
        return res

    def finalize(self):
        self.meta["date"] = self.get_date()
        self.meta["title"] = os.path.basename(self.src_relpath) or self.site.settings.SITE_NAME

    def render(self):
        self.subdirs.sort(key=lambda x: x.meta["title"])
        parent_page = None
        if self.src_relpath:
            parent = os.path.dirname(self.src_relpath)
            parent_page = self.site.pages.get(parent, None)

        body = self.site.theme.dir_template.render(
            parent_page=parent_page,
            page=self,
            pages=self.subdirs + self.pages,
        )
        return {
            self.dst_relpath: RenderedString(body)
        }

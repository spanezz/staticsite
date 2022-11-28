from __future__ import annotations
from typing import Dict, List, Any, Optional
from .utils import open_dir_fd
from .utils.typing import Meta
from . import file
from .page import Page, PageValidationError
from .site import Site
import functools
import stat
import os
import logging

log = logging.getLogger("contents")


def with_dir_fd(f):
    @functools.wraps(f)
    def wrapper(self, dir_fd: int):
        self.dir_fd = dir_fd
        try:
            return f(self, dir_fd)
        finally:
            self.dir_fd = None
    return wrapper


class Dir(Page):
    """
    Base class for content loaders
    """
    TYPE = "dir"

    def __init__(self, site: Site, src: file.File, meta: Meta, dir: Optional["Dir"] = None, name: Optional[str] = None):
        super().__init__(site, src, meta, dir=dir)
        # Directory name
        self.name: Optional[str] = name
        # Subdirectory of this directory
        self.subdirs: List["Dir"] = []
        # Files found in this directory
        self.files: Dict[str, file.File] = {}
        # Computed metadata for files and subdirectories
        self.file_meta: Dict[str, Meta] = {}
        # Set during methods when a dir_fd to this directory is present
        self.dir_fd: Optional[int] = None

        # Pages loaded from this directory
        self.pages = []

    @classmethod
    def create(
            cls,
            site: Site,
            src: file.File,
            meta: Dict[str, Any],
            dir: Optional["Dir"] = None,
            name: Optional[str] = None):
        # Check whether to load subdirectories as asset trees
        if meta.get("asset"):
            return AssetDir(site, src, meta, dir=dir, name=name)
        else:
            return ContentDir(site, src, meta, dir=dir, name=name)

    def finalize(self):
        # Finalize from the bottom up
        for subdir in self.subdirs:
            subdir.finalize()

        self.meta["pages"] = [p for p in self.pages if not p.meta["draft"]]
        self.meta.setdefault("template", "dir.html")
        self.meta["build_path"] = os.path.join(self.meta["site_path"], "index.html").lstrip("/")

        self.meta["indexed"] = bool(self.meta["pages"]) or any(p.meta["indexed"] for p in self.subdirs)
        self.meta.setdefault("syndicated", False)

        self.meta.setdefault("parent", self.dir)
        if self.dir is not None:
            self.meta["title"] = os.path.basename(self.src.relpath)

        # TODO: set draft if all subdirs and pages are drafts

        # Since finalize is called from the bottom up, subdirs have their date
        # up to date
        self.subdirs.sort(key=lambda p: p.meta["date"])
        self.meta["pages"].sort(key=lambda p: p.meta["date"])

        date_pages = []
        if self.subdirs:
            date_pages.append(self.subdirs[-1].meta["date"])
        if self.meta["pages"]:
            date_pages.append(self.meta["pages"][-1].meta["date"])

        if date_pages:
            self.meta["date"] = max(date_pages)
        else:
            self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)

        if self.meta["indexed"] and self.meta["site_path"] not in self.site.structure.pages:
            self.site.add_page(self)

    def validate(self):
        try:
            super().validate()
        except PageValidationError as e:
            log.error("%s: infrastructural page failed to validate: %s", e.page, e.msg)
            raise


class ContentDir(Dir):
    """
    Content path which uses features for content loading
    """


class AssetDir(ContentDir):
    """
    Content path which loads everything as assets
    """
    @with_dir_fd
    def scan(self, dir_fd: int):
        # Scan directory contents
        subdirs = {}
        with os.scandir(self.dir_fd) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    # Skip hidden directories
                    continue

                # Note: is_dir, is_file, and stat, follow symlinks by default
                if entry.is_dir():
                    # Take note of directories
                    subdirs[entry.name] = file.File.from_dir_entry(self.src, entry)
                else:
                    # Take note of files
                    self.files[entry.name] = file.File.from_dir_entry(self.src, entry)

        # TODO: build a directory page here? Or at site load time?
        # TODO: its contents can be added at analyze time

        # Scan subdirectories
        for name, src in subdirs.items():
            # Compute metadata for this directory
            meta: Meta = dict(self.meta)
            meta["site_path"] = os.path.join(meta["site_path"], name)

            # Recursively descend into the directory
            subdir = Dir.create(self.site, src, meta=meta, dir=self, name=name)
            with open_dir_fd(name, dir_fd=dir_fd) as subdir_fd:
                subdir.scan(subdir_fd)
            self.subdirs.append(subdir)

        # TODO: build (but not load) pages here?
        #       or hook into features here to keep track of the pages they want
        #       to load, and later just call the load method of each feature

    @with_dir_fd
    def load(self, dir_fd: int):
        """
        Read static assets from this directory and all its subdirectories

        Loader load assets directly without consulting features
        """
        from .asset import Asset

        site_path = self.meta["site_path"]

        log.debug("Loading pages from %s as %s", self.src.abspath, site_path)

        # Load every file as an asset
        for fname, f in self.files.items():
            if f.stat is None:
                continue
            if stat.S_ISREG(f.stat.st_mode):
                log.debug("Loading static file %s", f.relpath)
                p = Asset(self.site, f, meta={}, dir=self, name=fname)
                self.site.add_page(p)

        # Load subdirectories
        for subdir in self.subdirs:
            # TODO: prevent loops with a set of seen directory devs/inodes
            with open_dir_fd(os.path.basename(subdir.src.relpath), dir_fd=dir_fd) as subdir_fd:
                subdir.load(subdir_fd)

from __future__ import annotations
from typing import Dict, List, Any, Tuple, Optional
from .utils import front_matter, open_dir_fd
from .utils.typing import Meta
from .page_filter import compile_page_match
from . import file
from .page import Page, PageValidationError
from .site import Site
import functools
import stat
import os
import io
import re
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
        # Rules for assigning metadata to subdirectories
        self.dir_rules: List[Tuple[re.Pattern, Meta]] = []
        # Rules for assigning metadata to files
        self.file_rules: List[Tuple[re.Pattern, Meta]] = []
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

    def take_dir_rules(self, meta: Meta):
        """
        Acquire dir and file rules from meta, removing them from it
        """
        # Compile directory matching rules
        dir_meta = meta.pop("dirs", None)
        if dir_meta is None:
            dir_meta = {}
        self.dir_rules.extend((compile_page_match(k), v) for k, v in dir_meta.items())

        # Compute file matching rules
        file_meta = meta.pop("files", None)
        if file_meta is None:
            file_meta = {}
        self.file_rules.extend((compile_page_match(k), v) for k, v in file_meta.items())

    def meta_file(self, fname: str):
        # TODO: deprecate, and just use self.file_meta[fname]
        return self.file_meta[fname]

    def open(self, fname: str, src: file.File, *args, **kw):
        if self.dir_fd:
            def _file_opener(fname, flags):
                return os.open(fname, flags, dir_fd=self.dir_fd)
            return io.open(src.abspath, *args, opener=_file_opener, **kw)
        else:
            return io.open(src.abspath, *args, **kw)

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
    @with_dir_fd
    def scan(self, dir_fd: int):
        # Scan directory contents
        subdirs = {}
        with os.scandir(self.dir_fd) as entries:
            for entry in entries:
                # Note: is_dir, is_file, and stat, follow symlinks by default
                if entry.is_dir():
                    if entry.name.startswith("."):
                        # Skip hidden directories
                        continue
                    # Take note of directories
                    subdirs[entry.name] = file.File.from_dir_entry(self.src, entry)
                elif entry.name.startswith(".") and entry.name != ".staticsite":
                    # Skip hidden files
                    continue
                else:
                    # Take note of files
                    self.files[entry.name] = file.File.from_dir_entry(self.src, entry)

        # Load dir metadata from .staticsite, if present
        # TODO: move this to a feature implementing just load_dir_meta?
        dir_meta = {}

        dircfg: file.File = self.files.pop(".staticsite", None)
        if dircfg is not None:
            config: Dict[str, Any] = {}

            # Load .staticsite if found
            with self.open(".staticsite", dircfg, "rt") as fd:
                fmt, config = front_matter.read_whole(fd)

            self.take_dir_rules(config)
            dir_meta.update(config)

        # Let features add to directory metadata
        for feature in self.site.features.ordered():
            m = feature.load_dir_meta(self)
            if m is not None:
                self.take_dir_rules(m)
                dir_meta.update(m)

        # Merge in metadata, limited to inherited flags
        self.site.metadata.on_dir_meta(self, dir_meta)

        # Make sure site_path is absolute
        self.meta["site_path"] = os.path.join("/", self.meta["site_path"])

        # If site_name is not defined, use the root page title or the content
        # directory name
        if "site_name" not in self.meta:
            # Default site name to the root page title, if site name has not been
            # set yet
            # TODO: template_title is not supported (yet?)
            title = self.meta.get("title")
            if title is not None:
                self.meta["site_name"] = title
            else:
                self.meta["site_name"] = os.path.basename(self.src.abspath)

        self.site.theme.precompile_metadata_templates(self.meta)

        # TODO: build a directory page here? Or at site load time?
        # TODO: its contents can be added at analyze time

        # Scan subdirectories
        for name, src in subdirs.items():
            # Compute metadata for this directory
            meta: Meta = dict(self.meta)
            meta["site_path"] = os.path.join(meta["site_path"], name)
            for pattern, dmeta in self.dir_rules:
                if pattern.match(name):
                    meta.update(dmeta)

            # Recursively descend into the directory
            subdir = Dir.create(self.site, src, meta=meta, dir=self, name=name)
            with open_dir_fd(name, dir_fd=dir_fd) as subdir_fd:
                subdir.scan(subdir_fd)
            self.subdirs.append(subdir)

        # Compute metadata for files
        for fname in self.files.keys():
            res: Meta = {}
            for pattern, meta in self.file_rules:
                if pattern.match(fname):
                    res.update(meta)
            self.file_meta[fname] = res

        # TODO: build (but not load) pages here?
        #       or hook into features here to keep track of the pages they want
        #       to load, and later just call the load method of each feature

    @with_dir_fd
    def load(self, dir_fd: int):
        """
        Read static assets and pages from this directory and all its subdirectories

        Load files through features by default
        """
        from .asset import Asset

        site_path = self.meta["site_path"]

        log.debug("Loading pages from %s as %s", self.src.abspath, site_path)

        # Handle files marked as assets in their metadata
        taken = []
        for fname, f in self.files.items():
            meta = self.file_meta[fname]
            if meta and meta.get("asset"):
                p = Asset(self.site, f, meta=meta, dir=self, name=fname)
                self.site.add_page(p)
                taken.append(fname)
        for fname in taken:
            del self.files[fname]

        # Let features pick their files
        for handler in self.site.features.ordered():
            for page in handler.load_dir(self):
                self.site.add_page(page)
                if page.meta["indexed"]:
                    self.pages.append(page)
            if not self.files:
                break

        # Use everything else as an asset
        # TODO: move into an asset feature?
        site_path = self.meta["site_path"]
        for fname, f in self.files.items():
            if stat.S_ISREG(f.stat.st_mode):
                log.debug("Loading static file %s", f.relpath)
                meta = self.file_meta[fname]
                p = Asset(self.site, f, meta=meta, dir=self, name=fname)
                self.site.add_page(p)

        # TODO: warn of contents not loaded at this point?

        # Load subdirectories
        for subdir in self.subdirs:
            with open_dir_fd(os.path.basename(subdir.src.relpath), dir_fd=dir_fd) as subdir_fd:
                subdir.load(subdir_fd)


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

from __future__ import annotations
from typing import Dict, List, Any, Tuple
from .utils import front_matter, open_dir_fd
from .utils.typing import Meta
from .page_filter import compile_page_match
from . import site
from . import file
import stat
import os
import re
import logging

log = logging.getLogger("contents")


class ContentDir:
    """
    Base class for content loaders
    """
    def __init__(
            self, site: "site.Site", tree_root: str, relpath: str, dir_fd: int, meta: Dict[str, Any], dest_subdir=None):
        self.site = site
        self.tree_root = tree_root
        self.relpath = relpath
        self.dir_fd = dir_fd
        self.dest_subdir = dest_subdir
        # Subdirectory of this directory
        self.subdirs: List[str] = []
        # Files found in this directory
        self.files: Dict[str, file.File] = {}
        self.meta: Dict[str, Any] = meta
        # Rules for assigning metadata to subdirectories
        self.dir_rules: List[Tuple[re.Pattern, Meta]] = []
        # Rules for assigning metadata to files
        self.file_rules: List[Tuple[re.Pattern, Meta]] = []
        # Computed metadata for files and subdirectories
        self.file_meta: Dict[str, Meta] = {}

    def scan(self):
        # Scan directory contents
        with os.scandir(self.dir_fd) as entries:
            for entry in entries:
                # Note: is_dir, is_file, and stat, follow symlinks by default
                if entry.is_dir():
                    if entry.name.startswith("."):
                        # Skip hidden directories
                        continue
                    # Take note of directories
                    self.subdirs.append(entry.name)
                elif entry.name.startswith(".") and entry.name != ".staticsite":
                    # Skip hidden files
                    continue
                else:
                    # Take note of files
                    relpath = os.path.join(self.relpath, entry.name)
                    self.files[entry.name] = file.File(
                            relpath=relpath,
                            root=self.tree_root,
                            abspath=os.path.join(self.tree_root, relpath),
                            stat=entry.stat())

        # Load dir metadata from .staticsite, if present
        # TODO: move this to a feature implementing just load_dir_meta?
        dircfg = self.files.pop(".staticsite", None)
        if dircfg is not None:
            config: Dict[str, Any] = {}

            # Load .staticsite if found
            with open(dircfg.abspath, "rt", opener=self._file_opener) as fd:
                lines = [line.rstrip() for line in fd]
                fmt, config = front_matter.parse(lines)

            self.add_dir_config(config)

        # Lead features add to directory metadata
        for feature in self.site.features.ordered():
            feature.load_dir_meta(self)

        # If site_name is not defined, use the content directory name
        self.meta.setdefault("site_name", os.path.basename(self.tree_root))

        # Store directory metadata
        self.site.dir_meta[self.relpath] = self.meta

        # Compute metadata for directories
        for dname in self.subdirs:
            res: Dict[str, Any] = dict(self.meta)
            for pattern, meta in self.dir_rules:
                if pattern.match(dname):
                    res.update(meta)
            self.file_meta[dname] = res

        # Compute metadata for files
        for fname in self.files.keys():
            res: Dict[str, Any] = dict(self.meta)
            for pattern, meta in self.file_rules:
                if pattern.match(fname):
                    res.update(meta)
            self.file_meta[fname] = res

    def add_dir_config(self, meta: Meta):
        """
        Acquire directory configuration from a page metadata
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

        # Merge in metadata
        self.meta.update(meta)

        # Default site name to the root page title, if site name has not been
        # set yet
        # TODO: template_title is not supported (yet)
        title = meta.get("title")
        if title is not None:
            self.meta.setdefault("site_name", title)

    def meta_file(self, fname: str):
        # TODO: deprecate, and just use self.file_meta[fname]
        return self.file_meta[fname]

    def _file_opener(self, path, flags):
        return os.open(path, flags, dir_fd=self.dir_fd)

    def load(self):
        """
        Read static assets and pages from this directory and all its subdirectories

        Load files through features by default
        """
        from .asset import Asset

        log.debug("Loading pages from %s:%s", self.tree_root, self.relpath)

        # Load subdirectories
        for fname in self.subdirs:
            # Check whether to load subdirectories as asset trees
            meta = self.file_meta[fname]
            if meta.get("asset"):
                with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                    subdir = ContentDir(
                                self.site, self.tree_root, os.path.join(self.relpath, fname), subdir_fd, meta=meta)
                    subdir.scan()
                    subdir.load_assets()
            else:
                # TODO: prevent loops with a set of seen directory devs/inodes
                # Recurse
                with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                    subdir = ContentDir(
                                self.site, self.tree_root, os.path.join(self.relpath, fname), subdir_fd, meta=meta)
                    subdir.scan()
                    subdir.load()

        # Handle files marked as assets in their metadata
        taken = []
        for fname, f in self.files.items():
            meta = self.file_meta[fname]
            if meta and meta.get("asset"):
                p = Asset(self.site, f, meta=meta)
                if not p.is_valid():
                    continue
                self.site.add_page(p)
                taken.append(fname)
        for fname in taken:
            del self.files[fname]

        # Let features pick their files
        for handler in self.site.features.ordered():
            for page in handler.load_dir(self):
                self.site.add_page(page)
            if not self.files:
                break

        # Use everything else as an asset
        # TODO: move into an asset feature?
        for fname, f in self.files.items():
            if stat.S_ISREG(f.stat.st_mode):
                log.debug("Loading static file %s", f.relpath)
                p = Asset(self.site, f, meta=self.file_meta[fname])
                if not p.is_valid():
                    continue
                self.site.add_page(p)

        # TODO: warn of contents not loaded at this point?

    def load_assets(self):
        """
        Read static assets from this directory and all its subdirectories

        Loader load assets directly without consulting features
        """
        from .asset import Asset

        log.debug("Loading pages from %s:%s", self.tree_root, self.relpath)

        # Load subdirectories
        for fname in self.subdirs:
            # TODO: prevent loops with a set of seen directory devs/inodes
            # Recurse
            meta = self.file_meta.get(fname)
            with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                subdir = ContentDir(
                            self.site,
                            self.tree_root,
                            os.path.join(self.relpath, fname),
                            subdir_fd,
                            dest_subdir=self.dest_subdir, meta=meta)
                subdir.scan()
                subdir.load_assets()

        # Use everything else as an asset
        for fname, f in self.files.items():
            if stat.S_ISREG(f.stat.st_mode):
                log.debug("Loading static file %s", f.relpath)
                meta = self.file_meta.get(fname)
                p = Asset(self.site, f, dest_subdir=self.dest_subdir, meta=meta)
                if not p.is_valid():
                    continue
                self.site.add_page(p)

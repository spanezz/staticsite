from __future__ import annotations
from typing import Dict, List, Any
from .utils import front_matter, open_dir_fd
from .page_filter import compile_page_match
from . import site
from . import file
import stat
import os
import logging

log = logging.getLogger("contents")


class BaseDir:
    """
    Base class for content loaders
    """
    def __init__(self, site: "site.Site", tree_root: str, relpath: str, dir_fd: int, meta: Dict[str, Any]):
        self.site = site
        self.tree_root = tree_root
        self.relpath = relpath
        self.dir_fd = dir_fd
        self.subdirs: List[str] = []
        self.files: Dict[str, file.File] = {}
        self.meta: Dict[str, Any] = meta
        self.config: Dict[str, Any] = {}

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
                elif entry.name == ".staticsite":
                    # Load .staticsite if found
                    with open(entry.name, "rt", opener=self._file_opener) as fd:
                        lines = [line.rstrip() for line in fd]
                        fmt, self.config = front_matter.parse(lines)
                elif entry.name.startswith("."):
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

        # Read site metadata
        if "site" in self.config:
            self.meta.update(self.config["site"])

        # Postprocess directory metadata
        self.file_meta: Dict[str, Any] = {}

        # Compute metadata for files
        file_meta = self.config.get("files")
        if file_meta is None:
            file_meta = {}
        rules = [(compile_page_match(k), v) for k, v in file_meta.items()]
        for fname in self.files.keys():
            res: Dict[str, Any] = dict(self.meta)
            for pattern, meta in rules:
                if pattern.match(fname):
                    res.update(meta)
            self.file_meta[fname] = res

        # Compute metadata for directories
        dir_meta = self.config.get("dirs")
        if dir_meta is None:
            dir_meta = {}
        rules = [(compile_page_match(k), v) for k, v in dir_meta.items()]
        for dname in self.subdirs:
            res: Dict[str, Any] = dict(self.meta)
            for pattern, meta in rules:
                if pattern.match(dname):
                    res.update(meta)
            self.file_meta[dname] = res

    def meta_file(self, fname: str):
        # TODO: deprecate, and just use self.file_meta[fname]
        return self.file_meta[fname]

    def _file_opener(self, path, flags):
        return os.open(path, flags, dir_fd=self.dir_fd)


class ContentDir(BaseDir):
    """
    Loader for a content directory, loading files through features
    """
    def load(self):
        """
        Read static assets and pages from this directory and all its subdirectories
        """
        from .asset import Asset

        log.debug("Loading pages from %s:%s", self.tree_root, self.relpath)

        # Store directory metadata
        self.site.dirs[self.relpath] = self.meta

        # Load subdirectories
        for fname in self.subdirs:
            # Check whether to load subdirectories as asset trees
            meta = self.file_meta[fname]
            if meta.get("asset"):
                with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                    subdir = AssetDir(
                                self.site, self.tree_root, os.path.join(self.relpath, fname), subdir_fd, meta=meta)
                    subdir.load()
            else:
                # TODO: prevent loops with a set of seen directory devs/inodes
                # Recurse
                with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                    subdir = ContentDir(
                                self.site, self.tree_root, os.path.join(self.relpath, fname), subdir_fd, meta=meta)
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
        for fname, f in self.files.items():
            if stat.S_ISREG(f.stat.st_mode):
                log.debug("Loading static file %s", f.relpath)
                p = Asset(self.site, f, meta=self.file_meta[fname])
                if not p.is_valid():
                    continue
                self.site.add_page(p)


class AssetDir(BaseDir):
    """
    Loader for an asset directory, loading assets directly without consulting
    features
    """
    def __init__(self, *args, dest_subdir=None, **kw):
        super().__init__(*args, **kw)
        self.dest_subdir = dest_subdir

    def load(self):
        """
        Read static assets from this directory and all its subdirectories
        """
        from .asset import Asset

        log.debug("Loading pages from %s:%s", self.tree_root, self.relpath)

        # Store directory metadata
        self.site.dirs[self.relpath] = self.meta

        # Load subdirectories
        for fname in self.subdirs:
            # TODO: prevent loops with a set of seen directory devs/inodes
            # Recurse
            meta = self.file_meta.get(fname)
            with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                subdir = AssetDir(
                            self.site,
                            self.tree_root,
                            os.path.join(self.relpath, fname),
                            subdir_fd,
                            dest_subdir=self.dest_subdir, meta=meta)
                subdir.load()

        # Use everything else as an asset
        for fname, f in self.files.items():
            if stat.S_ISREG(f.stat.st_mode):
                log.debug("Loading static file %s", f.relpath)
                meta = self.file_meta.get(fname)
                p = Asset(self.site, f, dest_subdir=self.dest_subdir, meta=meta)
                if not p.is_valid():
                    continue
                self.site.add_page(p)

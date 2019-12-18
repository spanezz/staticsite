from __future__ import annotations
from typing import Optional, Dict, List, Any
from . import Site, File
from .utils import parse_front_matter, compile_page_match, open_dir_fd
import stat
import os
import logging

log = logging.getLogger("contents")


class BaseDir:
    """
    Base class for content loaders
    """
    def __init__(self, site: Site, tree_root: str, relpath: str, dir_fd: int):
        self.site = site
        self.tree_root = tree_root
        self.relpath = relpath
        self.dir_fd = dir_fd
        self.subdirs: List[str] = []
        self.files: Dict[str, File] = {}
        self.meta: Optional[Dict[str, Any]] = None

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
                        fmt, self.meta = parse_front_matter(lines)
                elif entry.name.startswith("."):
                    # Skip hidden files
                    continue
                else:
                    # Take note of files
                    relpath = os.path.join(self.relpath, entry.name)
                    self.files[entry.name] = File(
                            relpath=relpath,
                            root=self.tree_root,
                            abspath=os.path.join(self.tree_root, relpath),
                            stat=entry.stat())

        # Postprocess directory metadata
        self.file_meta = {}
        if self.meta is None:
            self.meta = {}
        else:
            # Compute metadata for files
            file_meta = self.meta.get("files")
            if file_meta is not None:
                rules = [(compile_page_match(k), v) for k, v in file_meta.items()]
                for fname in self.files.keys():
                    res = {}
                    for pattern, meta in rules:
                        if pattern.match(fname):
                            res.update(meta)
                    self.file_meta[fname] = res

            # Compute metadata for directories
            dir_meta = self.meta.get("dirs")
            if dir_meta is not None:
                rules = [(compile_page_match(k), v) for k, v in dir_meta.items()]
                for dname in self.subdirs:
                    res = {}
                    for pattern, meta in rules:
                        if pattern.match(dname):
                            res.update(meta)
                    self.file_meta[dname] = res

    def meta_file(self, fname: str):
        res = self.file_meta.get(fname)
        if res is None:
            return {}
        else:
            return res

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

        # Load subdirectories
        for fname in self.subdirs:
            # Check whether to load subdirectories as asset trees
            meta = self.file_meta.get(fname)
            if meta and meta.get("asset"):
                with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                    subdir = AssetDir(self.site, self.tree_root, os.path.join(self.relpath, fname), subdir_fd)
                    subdir.load()
            else:
                # TODO: prevent loops with a set of seen directory devs/inodes
                # Recurse
                with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                    subdir = ContentDir(self.site, self.tree_root, os.path.join(self.relpath, fname), subdir_fd)
                    subdir.load()

        # Handle files marked as assets in their metadata
        taken = []
        for fname, f in self.files.items():
            meta = self.file_meta.get(fname)
            if meta and meta.get("asset"):
                p = Asset(self.site, f, meta=meta)
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
                p = Asset(self.site, f, meta=self.file_meta.get(fname))
                self.site.add_page(p)


class AssetDir(BaseDir):
    """
    Loader for an asset directory, loading assets directly without consulting
    features
    """
    def load(self):
        """
        Read static assets from this directory and all its subdirectories
        """
        from .asset import Asset

        log.debug("Loading pages from %s:%s", self.tree_root, self.relpath)

        # Load subdirectories
        for fname in self.subdirs:
            # TODO: prevent loops with a set of seen directory devs/inodes
            # Recurse
            with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                subdir = AssetDir(self.site, self.tree_root, os.path.join(self.relpath, fname), subdir_fd)
                subdir.load()

        # Use everything else as an asset
        for fname, f in self.files.items():
            if stat.S_ISREG(f.stat.st_mode):
                log.debug("Loading static file %s", f.relpath)
                p = Asset(self.site, f, meta=self.file_meta.get(fname))
                self.site.add_page(p)

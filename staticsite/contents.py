from __future__ import annotations
from typing import NamedTuple, Optional, Dict, List, Tuple, Any
from . import Site, File
from .utils import parse_front_matter, compile_page_match, lazy, open_dir_fd
from pathlib import Path
import stat
import os
import logging

log = logging.getLogger("contents")


class ContentDir:
    def __init__(self, site: Site, tree_root: Path, relpath: Path, dir_fd: int):
        self.site = site
        self.tree_root = tree_root
        self.relpath = relpath
        self.dir_fd = dir_fd
        self.subdirs = []
        self.files = {}
        self.meta = None

        # Scan directory contents
        with os.scandir(self.dir_fd) as entries:
            for entry in entries:
                # Note: is_dir, is_file, and stat, follow symlinks by default
                if entry.is_dir():
                    # Take note of directories
                    self.subdirs.append(entry.name)
                elif entry.name == ".staticsite":
                    # Load .staticsite if found
                    with open(entry.name, "rt", opener=lambda path, flags: os.open(path, flags, dir_fd=self.dir_fd)) as fd:
                        lines = [line.rstrip() for line in fd]
                        fmt, self.meta = parse_front_matter(lines)
                else:
                    # Take note of files
                    self.files[entry.name] = File(
                            relpath=(relpath / entry.name).as_posix(),
                            root=self.tree_root.as_posix(),
                            abspath=(self.tree_root / relpath / entry.name).as_posix(),
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
                        if pattern.match(fname):
                            res.update(meta)
                    self.file_meta[fname] = res

    def meta_file(self, fname):
        res = self.file_meta.get(fname)
        if res is None:
            return {}
        else:
            return res

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
                # TODO
                ...
                # # Scan this subdir as an asset dir
                # for f in File.scan_subpath(d.tree_root, os.path.join(d.relpath, fname),
                #                            follow_symlinks=True, ignore_hidden=True):
                #     if not stat.S_ISREG(f.stat.st_mode):
                #         continue
                #     log.debug("Loading static file %s", f.relpath)
                #     self.add_page(Asset(self, f))
            else:
                # TODO: prevent loops with a set of seen directory devs/inodes
                # Recurse
                with open_dir_fd(fname, dir_fd=self.dir_fd) as subdir_fd:
                    subdir = ContentDir(self.site, self.tree_root, self.relpath / fname, subdir_fd)
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


#        with os.scandir(self.dir_fd) as entries:
#            for entry in entries:
#                print("FOUND", entry.name)
#                if entry.is_dir():
#                    with open_dir_fd(entry.name, dir_fd=self.dir_fd) as subdir_fd:
#                        subdir = ContentDir(self.site, self.tree_root, self.relpath / entry.name, subdir_fd)
#

from __future__ import annotations

import functools
import io
import logging
import os
import re
import stat
from typing import TYPE_CHECKING, Any, Optional

from . import file
from .page_filter import compile_page_match
from .utils import front_matter, open_dir_fd
from .utils.typing import Meta

if TYPE_CHECKING:
    from .site import Site

log = logging.getLogger("scan")


def with_dir_fd(f):
    """
    Set self.dir_fd for the duration of the function, and reset it afterwards
    """
    @functools.wraps(f)
    def wrapper(self, *, dir_fd: int, **kw):
        self.dir_fd = dir_fd
        try:
            return f(self, dir_fd=dir_fd, **kw)
        finally:
            self.dir_fd = None
    return wrapper


class Dir:
    """
    Source directory to be scanned
    """
    def __init__(self, src: file.File, meta: Meta):
        self.src = src
        self.meta: Meta = dict(meta) if meta else {}

    @classmethod
    def create(
            cls,
            src: file.File,
            meta: Meta):
        # Check whether to load subdirectories as asset trees
        if meta.get("asset"):
            return AssetDir(src, meta)
        else:
            return SourceDir(src, meta)

    @classmethod
    def scan_tree(cls, site: Site, src: file.File, meta: Meta):
        """
        Recursively scan a source tree
        """
        scanner = cls.create(src, meta)
        with open_dir_fd(src.abspath) as dir_fd:
            scanner.scan(site=site, dir_fd=dir_fd)

    def open(self, fname: str, src: file.File, *args, **kw):
        if self.dir_fd:
            def _file_opener(fname, flags):
                return os.open(fname, flags, dir_fd=self.dir_fd)
            return io.open(src.abspath, *args, opener=_file_opener, **kw)
        else:
            return io.open(src.abspath, *args, **kw)


class SourceDir(Dir):
    """
    Source directory to be scanned for pages and assets
    """
    @classmethod
    def take_dir_rules(
            self,
            dir_rules: list[tuple[re.Pattern, Meta]],
            file_rules: list[tuple[re.Pattern, Meta]],
            meta: Meta):
        """
        Acquire dir and file rules from meta, removing them from it
        """
        # Compile directory matching rules
        dir_meta = meta.pop("dirs", None)
        if dir_meta is None:
            dir_meta = {}
        dir_rules.extend((compile_page_match(k), v) for k, v in dir_meta.items())

        # Compute file matching rules
        file_meta = meta.pop("files", None)
        if file_meta is None:
            file_meta = {}
        file_rules.extend((compile_page_match(k), v) for k, v in file_meta.items())

    @with_dir_fd
    def scan(self, *, site: Site, dir_fd: int):
        # Scan directory contents
        dircfg: Optional[file.File] = None
        subdirs: dict[str, file.File] = {}
        files: dict[str, file.File] = {}
        # Rules for assigning metadata to subdirectories
        dir_rules: list[tuple[re.Pattern, Meta]] = []
        # Rules for assigning metadata to files
        file_rules: list[tuple[re.Pattern, Meta]] = []

        with os.scandir(self.dir_fd) as entries:
            for entry in entries:
                # Note: is_dir, is_file, and stat, follow symlinks by default
                if entry.is_dir():
                    if entry.name.startswith("."):
                        # Skip hidden directories
                        continue
                    # Take note of directories
                    subdirs[entry.name] = file.File.from_dir_entry(self.src, entry)
                elif entry.name == ".staticsite":
                    dircfg = file.File.from_dir_entry(self.src, entry)
                elif entry.name.startswith("."):
                    # Skip hidden files
                    continue
                else:
                    # Take note of files
                    files[entry.name] = file.File.from_dir_entry(self.src, entry)

        # Load dir metadata from .staticsite, if present
        # TODO: move this to a feature implementing just load_dir_meta?
        if dircfg is not None:
            config: dict[str, Any] = {}

            # Load .staticsite if found
            with self.open(".staticsite", dircfg, "rt") as fd:
                fmt, config = front_matter.read_whole(fd)

            self.take_dir_rules(dir_rules, file_rules, config)
            self.meta.update(config)

        # Let features add to directory metadata
        for feature in site.features.ordered():
            m = feature.load_dir_meta(self, files)
            if m is not None:
                self.take_dir_rules(dir_rules, file_rules, m)
                self.meta.update(m)

        # Merge in metadata, limited to inherited flags
        # TODO: site.metadata.on_dir_meta(self, self.meta)

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

        site.theme.precompile_metadata_templates(self.meta)

        # Scan subdirectories
        for name, src in subdirs.items():
            # Compute metadata for this directory
            meta: Meta = dict(self.meta)
            meta["site_path"] = os.path.join(meta["site_path"], name)
            for pattern, dmeta in dir_rules:
                if pattern.match(name):
                    meta.update(dmeta)

            # Recursively descend into the directory
            # subdir = SourceDir(src, meta=meta)
            subdir = Dir.create(src, meta=meta)  # TODO: see contents.Dir.create
            with open_dir_fd(name, dir_fd=dir_fd) as subdir_fd:
                subdir.scan(site=site, dir_fd=subdir_fd)

        # Compute metadata for files
        file_meta: dict[str, tuple[Meta, file.File]] = {}
        for fname, f in files.items():
            res: Meta = site.metadata.derive(self.meta)
            for pattern, meta in file_rules:
                if pattern.match(fname):
                    res.update(meta)
            file_meta[fname] = (res, f)

            # TODO: build (but not load) pages here?
            #       or hook into features here to keep track of the pages they want
            #       to load, and later just call the load method of each feature
        self.load(site, file_meta)

    def load(self, site: Site, files: dict[str, tuple[Meta, file.File]]):
        """
        Read static assets and pages from this directory and all its subdirectories

        Load files through features by default
        """
        from .asset import Asset

        site_path = self.meta["site_path"]

        log.debug("Loading pages from %s as %s", self.src.abspath, site_path)

        # Handle files marked as assets in their metadata
        taken = []
        for fname, (meta, f) in files.items():
            if meta and meta.get("asset"):
                p = Asset(site, src=f, meta=meta, src_dir=self, name=fname)
                site.add_page(p)
                taken.append(fname)
        for fname in taken:
            del files[fname]

        # Let features pick their files
        for handler in site.features.ordered():
            for page in handler.load_dir(self, files):
                site.add_page(page)
                # TODO: if page.meta["indexed"]:
                # TODO:     self.pages.append(page)
            if not files:
                break

        # Use everything else as an asset
        # TODO: move into an asset feature?
        site_path = self.meta["site_path"]
        for fname, (meta, f) in files.items():
            if f.stat and stat.S_ISREG(f.stat.st_mode):
                log.debug("Loading static file %s", f.relpath)
                p = Asset(site, src=f, meta=meta, src_dir=self, name=fname)
                site.add_page(p)

        # TODO: warn of contents not loaded at this point?


class AssetDir(Dir):
    """
    Source directory to be scanned for assets only
    """
    @with_dir_fd
    def scan(self, *, site: Site, dir_fd: int):
        subdirs: dict[str, file.File] = {}
        files: dict[str, file.File] = {}

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
                    files[entry.name] = file.File.from_dir_entry(self.src, entry)

        # TODO: build a directory page here? Or at site load time?
        # TODO: its contents can be added at analyze time

        # Scan subdirectories
        for name, src in subdirs.items():
            # Compute metadata for this directory
            meta: Meta = site.metadata.derive(self.meta)
            meta["site_path"] = os.path.join(self.meta["site_path"], name)

            # Recursively descend into the directory
            subdir = Dir.create(src, meta=meta)
            with open_dir_fd(name, dir_fd=dir_fd) as subdir_fd:
                subdir.scan(site=site, dir_fd=subdir_fd)

        self.load(site, files)

    def load(self, site: Site, files: dict[str, file.File]):
        """
        Read static assets from this directory and all its subdirectories

        Loader load assets directly without consulting features
        """
        from .asset import Asset

        site_path = self.meta["site_path"]

        log.debug("Loading pages from %s as %s", self.src.abspath, site_path)

        # Load every file as an asset
        for fname, src in files.items():
            if src.stat is None:
                continue
            if stat.S_ISREG(src.stat.st_mode):
                log.debug("Loading static file %s", src.relpath)
                p = Asset(site, src=src, meta={}, src_dir=self, name=fname)
                site.add_page(p)

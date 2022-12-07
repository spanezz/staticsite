from __future__ import annotations

import contextlib
import io
import logging
import os
import re
import stat
from typing import TYPE_CHECKING, Any, Optional, TextIO

from .file import File
from .page_filter import compile_page_match
from .utils import front_matter, open_dir_fd

if TYPE_CHECKING:
    from .site import Site
    from .page import Page
    from .node import Node

log = logging.getLogger("fstree")


class Tree:
    """
    Recursive information about a filesystem tree
    """
    def __init__(self, site: Site, src: File):
        self.site = site

        # When scanning/itearating, this is set to a path fd opened to this
        # directory
        self.dir_fd: Optional[int] = None

        # The directory corresponding to this node
        self.src = src

        # Metadata found in this directory
        self.meta = {}

        # Files in this directory
        self.files: dict[str, File] = {}

        # Subdirectories
        self.sub: dict[str, Tree] = {}

    def print(self, lead: str = "", file: Optional[TextIO] = None):
        for name, src in self.files.items():
            print(f"{lead}→ {name}", file=file)
        for name, tree in self.sub.items():
            print(f"{lead}📂 {name}", file=file)
            tree.print(lead + "  ", file=file)

    @contextlib.contextmanager
    def open_tree(self):
        """
        Open self.dir_fd for the duration of this context manager
        """
        with open_dir_fd(self.src.abspath) as dir_fd:
            self.dir_fd = dir_fd
            try:
                yield
            finally:
                self.dir_fd = None

    @contextlib.contextmanager
    def open_subtree(self, name: str, tree: Tree):
        """
        Open tree.dir_fd for the duration of this context manager
        """
        with open_dir_fd(name, self.dir_fd) as subdir_fd:
            tree.dir_fd = subdir_fd
            try:
                yield
            finally:
                tree.dir_fd = None

    def _scandir(self):
        """
        Scan the contents of a directory, filling in structures but without
        recursing
        """
        raise NotImplementedError(f"{self.__class__.__name__}._scandir not implemented")

    def scan(self):
        """
        Scan directory contents, recursively
        """
        self._scandir()
        # Recurse into subdirectories
        for name, tree in self.sub.items():
            with self.open_subtree(name, tree):
                tree.scan()

    def populate_node(self, node: Node):
        """
        Recursively popuplate the node with information from this tree
        """
        raise NotImplementedError(f"{self.__class__.__name__}.populate_node not implemented")

    def open(self, name, *args, **kw):
        """
        Open a file contained in this directory
        """
        if self.dir_fd is None:
            raise RuntimeError("Tree.open called without a dir_fd")

        def _file_opener(fname, flags):
            return os.open(fname, flags, dir_fd=self.dir_fd)
        return io.open(name, *args, opener=_file_opener, **kw)


class PageTree(Tree):
    """
    Filesystem tree that can contain pages and assets
    """
    def __init__(self, site: Site, src: File):
        super().__init__(site, src)

        # Rules for assigning metadata to subdirectories
        self.dir_rules: list[tuple[re.Pattern, dict[str, Any]]] = []

        # Rules for assigning metadata to files
        self.file_rules: list[tuple[re.Pattern, dict[str, Any]]] = []

    def _take_dir_rules(self, meta: dict[str, Any]):
        """
        Remove file and directory rules from the meta dict, and compile them
        for this Tree
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

    def _scandir(self):
        subdirs: list[tuple[str, File]] = []
        with os.scandir(self.dir_fd) as entries:
            for entry in entries:
                # Note: is_dir, is_file, and stat, follow symlinks by default
                if entry.is_dir():
                    if entry.name.startswith("."):
                        # Skip hidden directories
                        continue
                    # Take note of directories
                    subdirs.append((entry.name, File.from_dir_entry(self.src, entry)))
                elif entry.name == ".staticsite":
                    # Load dir metadata from .staticsite
                    with self.open(entry.name, "rt") as fd:
                        fmt, meta = front_matter.read_whole(fd)
                        self._take_dir_rules(meta)
                        self.meta.update(meta)
                elif entry.name.startswith("."):
                    # Skip hidden files
                    continue
                else:
                    # Take note of files
                    self.files[entry.name] = File.from_dir_entry(self.src, entry)

        # Let features add to node metadata
        #
        # This for example lets metadata of an index.md do the same work as a
        # .staticfile file
        for feature in self.site.features.ordered():
            meta = feature.load_dir_meta(self)
            if meta is not None:
                self._take_dir_rules(meta)
                self.meta.update(meta)

        # Instantiate subtrees
        for name, src in subdirs:
            meta = {}

            # Compute metadata for this directory
            for pattern, dmeta in self.dir_rules:
                if pattern.match(name):
                    meta.update(dmeta)

            if meta.get("asset"):
                self.sub[entry.name] = AssetTree(self.site, src)
            else:
                self.sub[entry.name] = PageTree(self.site, src)

    def populate_node(self, node: Node):
        # print(f"PageTree.populate_node {self.src.relpath=} {self.meta=}")
        # Add the metadata scanned for this directory
        node.update_meta(self.meta)

        # Compute metadata for files
        files_meta: dict[str, tuple[dict[str, Any], File]] = {}
        for fname, src in self.files.items():
            res: dict[str, Any] = {}
            for pattern, meta in self.file_rules:
                if pattern.match(fname):
                    res.update(meta)

            # Handle assets right away
            if res.get("asset"):
                # print(f"PageTree.populate_node  add asset {fname}")
                node.add_asset(src=src, name=fname)
            else:
                # print(f"PageTree.populate_node  enqueue file {fname}")
                files_meta[fname] = (res, src)

        # Let features pick their files
        # print(f"PageTree.populate_node  initial files to pick {files_meta.keys()}")
        for handler in self.site.features.ordered():
            handler.load_dir(node, self, files_meta)
            if not files_meta:
                break
        # print(f"PageTree.populate_node  remaining files to pick {files_meta.keys()}")

        # If no feature added a directory index, synthesize one
        dir_index: Optional[Page] = None
        if not node.page:
            dir_index = node.add_directory_index(self.src)

        # Use everything else as an asset
        # TODO: move into an asset feature?
        for fname, (file_meta, src) in files_meta.items():
            if src.stat and stat.S_ISREG(src.stat.st_mode):
                log.debug("Loading static file %s", src.relpath)
                node.add_asset(src=src, name=fname)

        # Recurse into subtrees
        for name, tree in self.sub.items():
            # Compute metadata for this directory
            dir_node = node.child(name)
            for pattern, dmeta in self.dir_rules:
                if pattern.match(name):
                    dir_node.update_meta(dmeta)

            with self.open_subtree(name, tree):
                tree.populate_node(dir_node)

        if dir_index:
            dir_index.analyze()


class AssetTree(Tree):
    """
    Filesystem tree that only contains assets
    """
    def _scandir(self):
        with os.scandir(self.dir_fd) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    # Skip hidden directories
                    continue

                # Note: is_dir, is_file, and stat, follow symlinks by default
                if entry.is_dir():
                    # Take note of directories
                    self.sub[entry.name] = AssetTree(self.site, File.from_dir_entry(self.src, entry))
                else:
                    # Take note of files
                    self.files[entry.name] = File.from_dir_entry(self.src, entry)

    def populate_node(self, node: Node):
        # Add the metadata scanned for this directory
        node.update_meta(self.meta)

        # Load every file as an asset
        for fname, src in self.files.items():
            if src.stat is None:
                continue
            if stat.S_ISREG(src.stat.st_mode):
                log.debug("Loading static file %s", src.relpath)
                node.add_asset(src=src, name=fname)

        # Recurse into subdirectories
        for name, tree in self.sub.items():
            # Compute metadata for this directory
            dir_node = node.child(name)

            # Recursively descend into the directory
            with self.open_subtree(name, tree):
                tree.populate_node(dir_node)

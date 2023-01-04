from __future__ import annotations

import contextlib
import io
import logging
import os
import re
import stat
from typing import (IO, TYPE_CHECKING, Any, Generator, Literal, Optional,
                    Union, overload)

from .file import File
from .utils import front_matter, open_dir_fd

if TYPE_CHECKING:
    from .site import Site
    from .source_node import SourceNode, SourcePageNode

log = logging.getLogger("fstree")


class Tree:
    """
    Recursive information about a filesystem tree
    """
    def __init__(self, *, site: Site, src: File, node: SourceNode):
        self.site = site
        self.node = node

        # When scanning/itearating, this is set to a path fd opened to this
        # directory
        self.dir_fd: Optional[int] = None

        # The directory corresponding to this node
        self.src = src

        # Files in this directory
        self.files: dict[str, File] = {}

        # Subdirectories
        self.sub: dict[str, Tree] = {}

    def print(self, lead: str = "", file: Optional[IO[str]] = None) -> None:
        print(f"{lead}", file=file)
        for name, src in self.files.items():
            print(f"{lead}→ {name}", file=file)
        for name, tree in self.sub.items():
            print(f"{lead}📂 {name}", file=file)
            tree.print(lead + "  ", file=file)

    @contextlib.contextmanager
    def open_tree(self) -> Generator[None, None, None]:
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
    def open_subtree(self, name: str, tree: Tree) -> Generator[None, None, None]:
        """
        Open tree.dir_fd for the duration of this context manager
        """
        with open_dir_fd(name, self.dir_fd) as subdir_fd:
            tree.dir_fd = subdir_fd
            try:
                yield
            finally:
                tree.dir_fd = None

    def _scandir(self) -> None:
        """
        Scan the contents of a directory, filling in structures but without
        recursing
        """
        raise NotImplementedError(f"{self.__class__.__name__}._scandir not implemented")

    def scan(self) -> None:
        """
        Scan directory contents, recursively
        """
        self._scandir()
        # Recurse into subdirectories
        for name, tree in self.sub.items():
            with self.open_subtree(name, tree):
                tree.scan()

    def populate_node(self) -> None:
        """
        Recursively popuplate the node with information from this tree
        """
        raise NotImplementedError(f"{self.__class__.__name__}.populate_node not implemented")

    @overload
    def open(self, name: str, mode: Literal["rt"]) -> IO[str]:
        ...

    @overload
    def open(self, name: str, mode: Literal["rb"]) -> IO[bytes]:
        ...

    def open(self, name: str, mode: str) -> Union[IO[str], IO[bytes]]:
        """
        Open a file contained in this directory
        """
        if self.dir_fd is None:
            raise RuntimeError("Tree.open called without a dir_fd")

        def _file_opener(fname: str, flags: int) -> int:
            return os.open(fname, flags, dir_fd=self.dir_fd)
        return io.open(name, mode=mode, opener=_file_opener)


class PageTree(Tree):
    """
    Filesystem tree that can contain pages and assets
    """
    def __init__(self, *, site: Site, src: File, node: SourcePageNode):
        super().__init__(site=site, src=src, node=node)
        self.node: SourcePageNode

        # Rules for assigning metadata to subdirectories
        self.dir_rules: list[tuple[re.Pattern[str], dict[str, Any]]] = []

        # Rules for assigning metadata to files
        self.file_rules: list[tuple[re.Pattern[str], dict[str, Any]]] = []

    def _take_dir_rules(self, meta: dict[str, Any]) -> None:
        """
        Remove file and directory rules from the meta dict, and compile them
        for this Tree
        """
        from .page_filter import compile_page_match

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

    def _load_dir_meta(self) -> dict[str, Any]:
        """
        Let features add to directory metadata

        This for example lets metadata of an index.md do the same work as a
        .staticfile file
        """
        res = {}
        for feature in self.site.features.ordered():
            meta = feature.load_dir_meta(self)
            if meta is not None:
                self._take_dir_rules(meta)
                res.update(meta)
        # Filter out metadata entries that were specific to the index page of the directory
        return {k: v for k, v in res.items() if k in self.node._fields}

    def _scandir(self) -> None:
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
                        # Honor skip: yes, completely skipping this subdir
                        if meta.get("skip", False):
                            return
                        self._take_dir_rules(meta)
                        self.node.update_fields(meta)
                elif entry.name.startswith("."):
                    # Skip hidden files
                    continue
                else:
                    # Take note of files
                    try:
                        self.files[entry.name] = File.from_dir_entry(self.src, entry)
                    except FileNotFoundError:
                        log.warning("%s: cannot stat() file: broken symlink?",
                                    os.path.join(self.src.abspath, entry.name))

        # Let features add to directory metadata
        self.node.update_fields(self._load_dir_meta())

        # Instantiate subtrees
        for name, src in subdirs:
            meta = {}

            # Compute metadata for this directory
            for pattern, dmeta in self.dir_rules:
                if pattern.match(name):
                    meta.update(dmeta)

            if meta.get("asset"):
                self.sub[name] = AssetTree(site=self.site, src=src, node=self.node.asset_child(name, src))
            else:
                self.sub[name] = PageTree(site=self.site, src=src, node=self.node.page_child(name, src))

    def populate_node(self) -> None:
        # Add the metadata scanned for this directory

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
                self.node.add_asset(src=src, name=fname)
            else:
                # print(f"PageTree.populate_node  enqueue file {fname}")
                files_meta[fname] = (res, src)

        # Create nodes for subtrees
        for name, tree in self.sub.items():
            # Compute metadata for this directory
            dir_node = self.node.sub[name]
            for pattern, dmeta in self.dir_rules:
                if pattern.match(name):
                    dir_node.update_fields(dmeta)

        # Let features pick their files
        # print(f"PageTree.populate_node  initial files to pick {files_meta.keys()}")
        for handler in self.site.features.ordered():
            handler.load_dir(self.node, self, files_meta)
            if not files_meta:
                break
        # print(f"PageTree.populate_node  remaining files to pick {files_meta.keys()}")

        # Use everything else as an asset
        # TODO: move into an asset feature?
        for fname, (file_meta, src) in files_meta.items():
            if src.stat and stat.S_ISREG(src.stat.st_mode):
                log.debug("Loading static file %s", src.relpath)
                self.node.add_asset(src=src, name=fname)

        # Recurse into subtrees
        for name, tree in self.sub.items():
            with self.open_subtree(name, tree):
                tree.populate_node()

        # If no feature added a directory index, synthesize one
        if not self.node.is_empty() and not self.node.page:
            self.node.add_directory_index(self.src)


class RootPageTree(PageTree):
    """
    Special behaviour of the root of the directory hierarchy
    """
    def _load_dir_meta(self) -> dict[str, Any]:
        res = super()._load_dir_meta()
        if (title := res.get("title")) and "site_name" not in res and not self.node.site_name:
            res["site_name"] = title
        return res


class AssetTree(Tree):
    """
    Filesystem tree that only contains assets
    """
    def __init__(self, *, site: Site, src: File, node: SourceNode):
        super().__init__(site=site, src=src, node=node)

    def _scandir(self) -> None:
        with os.scandir(self.dir_fd) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    # Skip hidden directories
                    continue

                # Note: is_dir, is_file, and stat, follow symlinks by default
                if entry.is_dir():
                    # Take note of directories
                    src = File.from_dir_entry(self.src, entry)
                    self.sub[entry.name] = AssetTree(
                            site=self.site,
                            src=src,
                            node=self.node.asset_child(entry.name, src))
                else:
                    # Take note of files
                    try:
                        self.files[entry.name] = File.from_dir_entry(self.src, entry)
                    except FileNotFoundError:
                        log.warning("%s: cannot stat() file: broken symlink?",
                                    os.path.join(self.src.abspath, entry.name))

    def populate_node(self) -> None:
        # Load every file as an asset
        for fname, src in self.files.items():
            if stat.S_ISREG(src.stat.st_mode):
                log.debug("Loading static file %s", src.relpath)
                self.node.add_asset(src=src, name=fname)

        # Recurse into subdirectories
        for name, tree in self.sub.items():
            # Recursively descend into the directory
            with self.open_subtree(name, tree):
                tree.populate_node()

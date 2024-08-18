from __future__ import annotations

import contextlib
import logging
import os
import re
import stat
from collections.abc import Generator
from typing import IO, TYPE_CHECKING, Any, Literal, overload

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
        self.dir_fd: int | None = None

        # The directory corresponding to this node
        self.src = src

        # Files in this directory
        self.files: dict[str, File] = {}

        # Subdirectories
        self.sub: dict[str, Tree] = {}

        # Rules for ignoring files
        self.ignore_rules: list[re.Pattern[str]] = []

    def print(self, lead: str = "", file: IO[str] | None = None) -> None:
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

    def _apply_ignore_rules(self) -> None:
        """
        Remove from self.files all entries that match self.ignore_rules
        """
        for name in list(self.files.keys()):
            for rule in self.ignore_rules:
                if rule.match(name):
                    del self.files[name]

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
        raise NotImplementedError(
            f"{self.__class__.__name__}.populate_node not implemented"
        )

    @overload
    def open(self, name: str, mode: Literal["rt"]) -> IO[str]:
        ...

    @overload
    def open(self, name: str, mode: Literal["rb"]) -> IO[bytes]:
        ...

    def open(self, name: str, mode: str) -> IO[str] | IO[bytes]:
        """
        Open a file contained in this directory
        """
        if self.dir_fd is None:
            raise RuntimeError("Tree.open called without a dir_fd")

        def _file_opener(fname: str, flags: int) -> int:
            return os.open(fname, flags, dir_fd=self.dir_fd)

        return open(name, mode=mode, opener=_file_opener)


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

        # Compute file ignore rules
        ignore = meta.pop("ignore", None)
        if ignore is None:
            ignore = []
        self.ignore_rules.extend(compile_page_match(k) for k in ignore)

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
                            self.files.clear()
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
                        log.warning(
                            "%s: cannot stat() file: broken symlink?",
                            os.path.join(self.src.abspath, entry.name),
                        )

        # Let features add to directory metadata
        self.node.update_fields(self._load_dir_meta())

        # Apply ignore rules
        self._apply_ignore_rules()

        # Instantiate subtrees
        for name, src in subdirs:
            meta = {}

            # Compute metadata for this directory
            for pattern, dmeta in self.dir_rules:
                if pattern.match(name):
                    meta.update(dmeta)

            node: SourceNode
            tree: Tree
            if meta.get("asset"):
                node = self.node.asset_child(name, src)
                tree = AssetTree(site=self.site, src=src, node=node)
            else:
                node = self.node.page_child(name, src)
                tree = PageTree(site=self.site, src=src, node=node)

            # Inherit ignore rules
            tree.ignore_rules.extend(self.ignore_rules)

            node.update_fields(meta)
            self.sub[name] = tree

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

        # Recurse into subtrees
        for name, tree in self.sub.items():
            with self.open_subtree(name, tree):
                tree.populate_node()

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

        self.node.prune_empty_subnodes()


class RootPageTree(PageTree):
    """
    Special behaviour of the root of the directory hierarchy
    """

    def _load_dir_meta(self) -> dict[str, Any]:
        res = super()._load_dir_meta()
        if (
            (title := res.get("title"))
            and "site_name" not in res
            and not self.node.site_name
        ):
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
                    tree = AssetTree(
                        site=self.site,
                        src=src,
                        node=self.node.asset_child(entry.name, src),
                    )
                    tree.ignore_rules.extend(self.ignore_rules)
                    self.sub[entry.name] = tree
                else:
                    # Take note of files
                    try:
                        self.files[entry.name] = File.from_dir_entry(self.src, entry)
                    except FileNotFoundError:
                        log.warning(
                            "%s: cannot stat() file: broken symlink?",
                            os.path.join(self.src.abspath, entry.name),
                        )

        # Apply ignore rules
        self._apply_ignore_rules()

    def populate_node(self) -> None:
        # Recurse into subdirectories
        for name, tree in self.sub.items():
            # Recursively descend into the directory
            with self.open_subtree(name, tree):
                tree.populate_node()

        # Load every file as an asset
        for fname, src in self.files.items():
            if stat.S_ISREG(src.stat.st_mode):
                log.debug("Loading static file %s", src.relpath)
                self.node.add_asset(src=src, name=fname)

        self.node.prune_empty_subnodes()

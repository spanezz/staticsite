from __future__ import annotations
from typing import NamedTuple, Optional, Dict, List, Tuple, Any
from .utils import parse_front_matter, compile_page_match, lazy
import re
import os


class Dir:
    """
    Information about one directory during scanning
    """
    def __init__(self, tree_root: str, relpath: str, subdirs: List[str], files: Dict[str, "File"], dirfd=int):
        self.tree_root = tree_root
        self.relpath = relpath
        # List of subdirectory names. Remove a name from the list to avoid recursing into it
        self.subdirs = subdirs

        # load .staticsite from dir if it exists
        file_meta = files.pop(".staticsite", None)
        if file_meta:
            with open(file_meta.abspath, "rt") as fd:
                lines = [line.rstrip() for line in fd]
                fmt, self.meta = parse_front_matter(lines)
        else:
            self.meta = {}

        self.files = files

        # Cache of file metadata computed from .staticsite contents
        self._file_meta_cache = {}

    @lazy
    def meta_features(self):
        """
        Return a dict with the 'features'-specific metadata
        """
        res = self.meta.get("features")
        if res is None:
            return {}
        return res

    @lazy
    def meta_files(self) -> List[Tuple[re.Pattern, Dict[str, Any]]]:
        """
        Return a list of tuples with filename matching regexps and associated
        metadata
        """
        res = self.meta.get("files")
        if res is None:
            return ()
        return [(compile_page_match(k), v) for k, v in res.items()]

    def meta_file(self, fname):
        """
        Return a dict with the dir metadata related to a file
        """
        # Lookup in cache to avoid computing it twice
        res = self._file_meta_cache.get(fname)
        if res is None:
            # Compute and add to cache
            res = {}
            for pattern, meta in self.meta_files:
                if pattern.match(fname):
                    res.update(meta)
            self._file_meta_cache[fname] = res
        return res

    @lazy
    def meta_dirs(self) -> List[Tuple[re.Pattern, Dict[str, Any]]]:
        """
        Return a list of tuples with filename matching regexps and associated
        metadata
        """
        res = self.meta.get("dirs")
        if res is None:
            return ()
        return [(compile_page_match(k), v) for k, v in res.items()]

    def meta_dir(self, fname):
        """
        Return a dict with the dir metadata related to a directory
        """
        # Lookup in cache to avoid computing it twice
        res = self._file_meta_cache.get(fname)
        if res is None:
            # Compute and add to cache
            res = {}
            for pattern, meta in self.meta_dirs:
                if pattern.match(fname):
                    res.update(meta)
            self._file_meta_cache[fname] = res
        return res


class File(NamedTuple):
    """
    Information about a file in the file system.

    If stat is not None, the file exists and these are its stats.
    """
    # Relative path to root
    relpath: str
    # Root of the directory tree where the file was scanned
    root: Optional[str] = None
    # Absolute path to the file
    abspath: Optional[str] = None
    # File stats if the file exists, else NOne
    stat: Optional[os.stat_result] = None

    def __str__(self):
        if self.abspath:
            return self.abspath
        else:
            return f"{self.root} → {self.relpath}"

    @classmethod
    def from_abspath(cls, tree_root: str, abspath: str):
        return cls(
                relpath=os.path.relpath(abspath, tree_root),
                root=tree_root,
                abspath=abspath)

    @classmethod
    def scan_dirs(cls, tree_root, relpath=None, follow_symlinks=False, ignore_hidden=False):
        if relpath is None:
            scan_path = tree_root
        else:
            scan_path = os.path.join(tree_root, relpath)

        for root, subdirs, fnames, dirfd in os.fwalk(scan_path, follow_symlinks=follow_symlinks):
            if ignore_hidden:
                # Ignore hidden directories
                filtered = [d for d in subdirs if not d.startswith(".")]
                if len(filtered) != len(subdirs):
                    subdirs[::] = filtered

            files = {}
            for f in fnames:
                # Ignore hidden files
                if ignore_hidden and f.startswith(".") and f != ".staticsite":
                    continue

                abspath = os.path.join(root, f)
                try:
                    st = os.stat(f, dir_fd=dirfd)
                except FileNotFoundError:
                    # Skip broken links
                    continue
                files[f] = cls(
                        relpath=os.path.relpath(abspath, tree_root),
                        root=tree_root,
                        abspath=abspath,
                        stat=st)

            yield Dir(
                    tree_root=tree_root,
                    relpath=os.path.relpath(root, tree_root),
                    subdirs=subdirs,
                    files=files,
                    dirfd=dirfd)

    @classmethod
    def scan(cls, tree_root, follow_symlinks=False, ignore_hidden=False):
        """
        Scan tree_root, generating relative paths based on it
        """
        for root, dnames, fnames, dirfd in os.fwalk(tree_root, follow_symlinks=follow_symlinks):
            if ignore_hidden:
                # Ignore hidden directories
                filtered = [d for d in dnames if not d.startswith(".")]
                if len(filtered) != len(dnames):
                    dnames[::] = filtered

            for f in fnames:
                # Ignore hidden files
                if ignore_hidden and f.startswith("."):
                    continue

                abspath = os.path.join(root, f)
                try:
                    st = os.stat(f, dir_fd=dirfd)
                except FileNotFoundError:
                    # Skip broken links
                    continue
                yield cls(
                        relpath=os.path.relpath(abspath, tree_root),
                        root=tree_root,
                        abspath=abspath,
                        stat=st)

    @classmethod
    def scan_subpath(cls, tree_root, relpath, follow_symlinks=False, ignore_hidden=False):
        """
        Scan a subdirectory of tree_root, generating relative paths based on tree_root
        """
        scan_path = os.path.join(tree_root, relpath)
        for root, dnames, fnames, dirfd in os.fwalk(scan_path, follow_symlinks=follow_symlinks):
            if ignore_hidden:
                # Ignore hidden directories
                filtered = [d for d in dnames if not d.startswith(".")]
                if len(filtered) != len(dnames):
                    dnames[::] = filtered

            for f in fnames:
                # Ignore hidden files
                if ignore_hidden and f.startswith("."):
                    continue

                abspath = os.path.join(relpath, root, f)
                try:
                    st = os.stat(f, dir_fd=dirfd)
                except FileNotFoundError:
                    # Skip broken links
                    continue
                yield cls(
                        relpath=os.path.relpath(abspath, tree_root),
                        root=tree_root,
                        abspath=abspath,
                        stat=st)

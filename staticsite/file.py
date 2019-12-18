from __future__ import annotations
from typing import NamedTuple, Optional
import os


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

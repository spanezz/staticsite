from __future__ import annotations

import logging
import os
from collections.abc import Generator
from typing import NamedTuple

log = logging.getLogger("contents")


class File(NamedTuple):
    """
    Information about a file in the file system.

    If stat is not None, the file exists and these are its stats.
    """

    # Relative path to root
    relpath: str
    # Absolute path to the file
    abspath: str
    # File stats if the file exists, else None
    stat: os.stat_result

    def __str__(self) -> str:
        if self.abspath:
            return self.abspath
        else:
            return self.relpath

    @classmethod
    def from_dir_entry(cls, dir: File, entry: os.DirEntry[str]) -> File:
        return cls(
            relpath=os.path.join(dir.relpath, entry.name),
            abspath=os.path.join(dir.abspath, entry.name),
            stat=entry.stat(),
        )

    @classmethod
    def with_stat(cls, relpath: str, abspath: str) -> File:
        return cls(relpath, abspath, os.stat(abspath))

    @classmethod
    def scan(
        cls, abspath: str, follow_symlinks: bool = False, ignore_hidden: bool = False
    ) -> Generator[File, None, None]:
        """
        Scan tree_root, generating relative paths based on it
        """
        for root, dnames, fnames, dirfd in os.fwalk(
            abspath, follow_symlinks=follow_symlinks
        ):
            if ignore_hidden:
                # Ignore hidden directories
                filtered = [d for d in dnames if not d.startswith(".")]
                if len(filtered) != len(dnames):
                    dnames[::] = filtered

            for f in fnames:
                # Ignore hidden files
                if ignore_hidden and f.startswith("."):
                    continue

                try:
                    st = os.stat(f, dir_fd=dirfd)
                except FileNotFoundError:
                    # Skip broken links
                    continue
                relpath = os.path.join(root, f)
                yield cls(
                    relpath=relpath, abspath=os.path.join(abspath, relpath), stat=st
                )

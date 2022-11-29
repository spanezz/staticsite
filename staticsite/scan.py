from __future__ import annotations

import functools
import io
import logging
import os
import re
import stat
from typing import TYPE_CHECKING, Optional, Any

from . import file, dirindex
from .page_filter import compile_page_match
from .utils import front_matter, open_dir_fd
from .metadata import Meta

if TYPE_CHECKING:
    from . import structure
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


def scan_tree(site: Site, src: file.File, node: Optional[structure.Node] = None):
    """
    Recursively scan a source tree
    """
    if node is None:
        node = site.structure.root

    # Add src to the node if it was missing
    if node.src is None:
        node.src = src

    with open_dir_fd(src.abspath) as dir_fd:
        scan(site=site, directory=Directory(src, dir_fd), node=node)


def scan(*, node: structure.Node, **kw):
    if node.meta.get("asset"):
        scan_assets(node=node, **kw)
    else:
        scan_pages(node=node, **kw)


class Directory:
    """
    Fast accessor to files in a directory
    """
    def __init__(self, src: file.File, dir_fd: int):
        # The directory itself
        self.src = src
        # dir_fd for fast access to contents
        self.dir_fd = dir_fd
        # File pointing to a .staticsite file, if present
        self.dircfg: Optional[file.File] = None
        # Subdirectories
        self.subdirs: dict[str, file.File] = {}
        # Plain files
        self.files: dict[str, file.File] = {}

        # Scan directory contents
        with os.scandir(dir_fd) as entries:
            for entry in entries:
                # Note: is_dir, is_file, and stat, follow symlinks by default
                if entry.is_dir():
                    if entry.name.startswith("."):
                        # Skip hidden directories
                        continue
                    # Take note of directories
                    self.subdirs[entry.name] = file.File.from_dir_entry(src, entry)
                elif entry.name == ".staticsite":
                    self.dircfg = file.File.from_dir_entry(src, entry)
                elif entry.name.startswith("."):
                    # Skip hidden files
                    continue
                else:
                    # Take note of files
                    self.files[entry.name] = file.File.from_dir_entry(src, entry)

    def open(self, name, *args, **kw):
        """
        Open a file contained in this directory
        """
        def _file_opener(fname, flags):
            return os.open(fname, flags, dir_fd=self.dir_fd)
        return io.open(os.path.join(self.src.abspath, name), *args, opener=_file_opener, **kw)


def take_dir_rules(
        dir_rules: list[tuple[re.Pattern, Meta]],
        file_rules: list[tuple[re.Pattern, Meta]],
        data: dict[str, Any]):
    """
    Acquire dir and file rules from meta, removing them from it
    """
    # Compile directory matching rules
    dir_meta = data.pop("dirs", None)
    if dir_meta is None:
        dir_meta = {}
    dir_rules.extend((compile_page_match(k), v) for k, v in dir_meta.items())

    # Compute file matching rules
    file_meta = data.pop("files", None)
    if file_meta is None:
        file_meta = {}
    file_rules.extend((compile_page_match(k), v) for k, v in file_meta.items())


def scan_pages(*, site: Site, directory: Directory, node: structure.Node):
    """
    Scan for pages and assets
    """
    # Rules for assigning metadata to subdirectories
    dir_rules: list[tuple[re.Pattern, Meta]] = []
    # Rules for assigning metadata to files
    file_rules: list[tuple[re.Pattern, Meta]] = []

    # Load dir metadata from .staticsite
    if directory.dircfg is not None:
        config: dict[str, Any]

        # Load .staticsite if found
        with directory.open(".staticsite", "rt") as fd:
            fmt, config = front_matter.read_whole(fd)

        take_dir_rules(dir_rules, file_rules, config)
        node.meta.update(config)

    # Let features add to node metadata
    #
    # This for example lets metadata of an index.md do the same work as a
    # .staticfile file
    for feature in site.features.ordered():
        m = feature.load_dir_meta(directory)
        if m is not None:
            take_dir_rules(dir_rules, file_rules, m)
            node.meta.update(m)

    # Make sure site_path is absolute
    node.meta["site_path"] = os.path.join("/", node.meta["site_path"])

    # If site_name is not defined, use the root page title or the content
    # directory name
    if "site_name" not in node.meta:
        # Default site name to the root page title, if site name has not been
        # set yet
        # TODO: template_title is not supported (yet?)
        title = node.meta.get("title")
        if title is not None:
            node.meta["site_name"] = title
        else:
            node.meta["site_name"] = os.path.basename(directory.src.abspath)

    site.theme.precompile_metadata_templates(node.meta.values)

    # Compute metadata for files
    files_meta: dict[str, tuple[Meta, file.File]] = {}
    for fname, src in directory.files.items():
        res: Meta = node.meta.derive()
        for pattern, meta in file_rules:
            if pattern.match(fname):
                res.update(meta)

        # Handle assets right away
        if res.get("asset"):
            node.add_asset(src=src, name=fname, parent_meta=node.meta)
        else:
            files_meta[fname] = (res, src)

    # Let features pick their files
    for handler in site.features.ordered():
        handler.load_dir(node, directory, files_meta)
        if not files_meta:
            break

    if not node.sub or "index.html" not in node.sub:
        dirindex.Dir.create(node, directory)

    # Use everything else as an asset
    # TODO: move into an asset feature?
    for fname, (file_meta, src) in files_meta.items():
        if src.stat and stat.S_ISREG(src.stat.st_mode):
            log.debug("Loading static file %s", src.relpath)
            node.add_asset(src=src, name=fname, parent_meta=node.meta)
    # Recurse into subdirectories
    for name, src in directory.subdirs.items():
        # Compute metadata for this directory
        dir_node = node.child(name, src=src)
        dir_node.meta["site_path"] = os.path.join(node.meta["site_path"], name)
        for pattern, dmeta in dir_rules:
            if pattern.match(name):
                dir_node.meta.update(dmeta)

        # Recursively descend into the directory
        with open_dir_fd(name, dir_fd=directory.dir_fd) as subdir_fd:
            scan(site=site, directory=Directory(src, subdir_fd), node=dir_node)

    # TODO: warn of contents not loaded at this point?

    # If we didn't load an index, create a default directory index
    # TODO: delegate to Dir feature's load_dir, set to running as after all
    # other features


def scan_assets(*, site: Site, directory: Directory, node: structure.Node):
    """
    Scan for assets only
    """
    # TODO: build a directory page here? Or at site load time?
    # TODO: its contents can be added at analyze time

    # Load every file as an asset
    for fname, src in directory.files.items():
        if src.stat is None:
            continue
        if stat.S_ISREG(src.stat.st_mode):
            log.debug("Loading static file %s", src.relpath)
            node.add_asset(src=src, name=fname, parent_meta=node.meta)

    # Recurse into subdirectories
    for name, src in directory.subdirs.items():
        # Compute metadata for this directory
        dir_node = node.child(name, src=src)
        dir_node.meta["site_path"] = os.path.join(node.meta["site_path"], name)

        # Recursively descend into the directory
        with open_dir_fd(name, dir_fd=directory.dir_fd) as subdir_fd:
            scan(site=site, directory=Directory(src, subdir_fd), node=dir_node)

from __future__ import annotations

import datetime
import io
import logging
import os
import stat
from typing import TYPE_CHECKING, Optional, TextIO

from . import fields, file
from .node import Node, SkipPage
from .site import Path
from .utils import open_dir_fd

if TYPE_CHECKING:
    from .asset import Asset
    from .site import Site

log = logging.getLogger("node")


class SourceNode(Node):
    """
    Node corresponding to a source directory
    """
    def __init__(self, site: Site, name: str, *, src: file.File, parent: Optional[Node]):
        super().__init__(site, name, parent=parent)

        # The directory corresponding to this node
        self.src = src

    def populate(self):
        """
        Recursively populate the node with information from this tree
        """
        raise NotImplementedError(f"{self.__class__.__name__}.populate not implemented")

    def add_asset(self, *, src: file.File, name: str) -> Asset:
        """
        Add an Asset as a subnode of this one
        """
        # Import here to avoid cyclical imports
        from .asset import Asset
        return self.create_source_page_as_file(page_cls=Asset, src=src, name=name, dst=name)

    def create_source_page_as_file(
            self, *,
            src: file.File,
            dst: str,
            date: Optional[datetime.datetime] = None,
            **kw):
        """
        Create a page of the given type, attaching it at the given path
        """
        if "created_from" in kw:
            raise RuntimeError("source page created with 'created_from' set")

        if self.site.last_load_step > self.site.LOAD_STEP_CONTENTS:
            raise RuntimeError("Node.create_source_page created after the 'contents' step has completed")

        if self.site.previous_source_footprints:
            # TODO: since we pop, we lose fooprint info for assets that replace other assets.
            # TODO: propagate it when doing the replacement?
            kw["old_footprint"] = self.site.previous_source_footprints.pop(src.relpath, None)

        if date is None:
            date = self.site.localized_timestamp(src.stat.st_mtime)
        else:
            date = self.site.clean_date(date)

        # Skip draft pages
        if date > self.site.generation_time and not self.site.settings.DRAFT_MODE:
            log.info("%s: page is still a draft: skipping", src.relpath)
            return None

        try:
            return self._create_leaf_page(dst=dst, src=src, date=date, **kw)
        except SkipPage:
            return None

    def asset_child(self, name: str, src: file.File) -> SourceAssetNode:
        """
        Create the given child as a SourceNode
        """
        if (node := self.sub.get(name)) is not None:
            if not isinstance(node, SourceNode):
                raise RuntimeError(
                        f"source node {name} already exists in {self.name}"
                        f" as virtual node instead of source node {src.abspath}")
            if node.src != src:
                log.debug("assets: merging %s with %s", node.src.abspath, src.abspath)
                # Replace src, since for assets we allow merging multiple dirs
                node.src = src
            return node

        node = self.site.features.get_node_class(SourceAssetNode)(site=self.site, name=name, parent=self, src=src)
        self.sub[name] = node
        return node


class SourceAssetNode(SourceNode):
    """
    Node corresponding to a source directory that contains only asset pages
    """
    def populate_node(self, node: SourceAssetNode):
        # Add the metadata scanned for this directory
        for k, v in self.meta.items():
            if k in node._fields:
                setattr(node, k, v)

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
            dir_node = node.asset_child(name, src=tree.src)

            # Recursively descend into the directory
            with self.open_subtree(name, tree):
                tree.populate_node(dir_node)


class SourcePageNode(SourceNode):
    """
    Node corresponding to a source directory that contains non-asset pages
    """
    def create_source_page_as_path(
            self,
            src: file.File,
            name: str,
            date: Optional[datetime.datetime] = None,
            **kw):
        """
        Create a page of the given type, attaching it at the given path
        """
        if "created_from" in kw:
            raise RuntimeError("source page created with 'created_from' set")

        if self.site.last_load_step > self.site.LOAD_STEP_CONTENTS:
            raise RuntimeError("Node.create_source_page created after the 'contents' step has completed")

        if self.site.previous_source_footprints:
            # TODO: since we pop, we lose fooprint info for assets that replace other assets.
            # TODO: propagate it when doing the replacement?
            kw["old_footprint"] = self.site.previous_source_footprints.pop(src.relpath, None)

        if date is None:
            date = self.site.localized_timestamp(src.stat.st_mtime)
        else:
            date = self.site.clean_date(date)

        # Skip draft pages
        if date > self.site.generation_time and not self.site.settings.DRAFT_MODE:
            log.info("%s: page is still a draft: skipping", src.relpath)
            return None

        node = self._child(name)

        try:
            return node._create_index_page(directory_index=False, src=src, date=date, **kw)
        except SkipPage:
            return None

    def create_source_page_as_index(
            self,
            src: file.File,
            date: Optional[datetime.datetime] = None,
            **kw):
        """
        Create a page of the given type, attaching it at the given path
        """
        if "created_from" in kw:
            raise RuntimeError("source page created with 'created_from' set")

        if self.site.last_load_step > self.site.LOAD_STEP_CONTENTS:
            raise RuntimeError("Node.create_source_page created after the 'contents' step has completed")

        if self.site.previous_source_footprints:
            # TODO: since we pop, we lose fooprint info for assets that replace other assets.
            # TODO: propagate it when doing the replacement?
            kw["old_footprint"] = self.site.previous_source_footprints.pop(src.relpath, None)

        if date is None:
            date = self.site.localized_timestamp(src.stat.st_mtime)
        else:
            date = self.site.clean_date(date)

        # Skip draft pages
        if date > self.site.generation_time and not self.site.settings.DRAFT_MODE:
            log.info("%s: page is still a draft: skipping", src.relpath)
            return None

        try:
            return self._create_index_page(directory_index=True, src=src, date=date, **kw)
        except SkipPage:
            return None

    def add_directory_index(self, src: file.File):
        """
        Add a directory index to this node
        """
        from . import dirindex
        return self.create_source_page_as_index(
            page_cls=dirindex.Dir,
            name=self.name,
            src=src)

    def page_child(self, name: str, src: file.File) -> SourcePageNode:
        """
        Create the given child as a SourceNode
        """
        if (node := self.sub.get(name)) is not None:
            if not isinstance(node, SourceNode):
                raise RuntimeError(
                        f"source node {name} already exists in {self.name}"
                        f" as virtual node instead of source node {src.abspath}")
            if node.src != src:
                raise RuntimeError(
                        f"source node {name} already exists in {self.name}"
                        f" as {node.src.abspath} instead of {src.abspath}")
            return node

        node = self.site.features.get_node_class(SourcePageNode)(site=self.site, name=name, parent=self, src=src)
        self.sub[name] = node
        return node


class RootNode(SourcePageNode):
    """
    Node at the root of the site tree
    """
    title = fields.Field["Node", str](doc="""
        Title used as site name.

        This only makes sense for the root node of the site hierarchy, and
        takes the value from the title of the root index page. If set, and the
        site name is not set by other means, it is used to give the site a name.
    """)

    def __init__(self, site: Site, *, src: file.File):
        super().__init__(site, name="", src=src, parent=None)

    def root_for_site_path(self, path: Path) -> SourceNode:
        """
        Return the subnode at the given path, creating it if missing
        """
        res: SourceNode = self
        while path:
            res = self.page_child(path.head, src=self.src)
            path = path.tail
        return res

    def static_root(self, path: Path) -> SourceNode:
        """
        Return the subnode at the given path, creating it if missing
        """
        res: SourceNode = self
        while path:
            res = res.asset_child(path.head, src=self.src)
            path = path.tail
        return res

    def generate_path(self, path: Path) -> Node:
        """
        Return the subnode at the given path, creating it if missing
        """
        res: Node = self
        while path:
            res = res._child(path.head)
            path = path.tail
        return res

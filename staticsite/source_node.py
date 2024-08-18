from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any, TypeVar

from . import fields, file
from .node import Node, SkipPage
from .site import Path

if TYPE_CHECKING:
    from .asset import Asset
    from .page import Page
    from .site import Site

log = logging.getLogger("node")

P = TypeVar("P", bound="Page")


class SourceNode(Node):
    """
    Node corresponding to a source directory
    """

    def add_asset(self, *, src: file.File, name: str) -> Asset | None:
        """
        Add an Asset as a subnode of this one
        """
        # Import here to avoid cyclical imports
        from .asset import Asset

        return self.create_source_page_as_file(
            page_cls=Asset, src=src, name=name, dst=name
        )

    def create_source_page_as_file(
        self,
        *,
        page_cls: type[P],
        src: file.File,
        dst: str,
        date: datetime.datetime | None = None,
        **kw: Any,
    ) -> P | None:
        """
        Create a page of the given type, attaching it at the given path
        """
        if "created_from" in kw:
            raise RuntimeError("source page created with 'created_from' set")

        if self.site.last_load_step > self.site.LOAD_STEP_CONTENTS:
            raise RuntimeError(
                "Node.create_source_page created after the 'contents' step has completed"
            )

        if self.site.previous_source_footprints:
            # TODO: since we pop, we lose fooprint info for assets that replace other assets.
            # TODO: propagate it when doing the replacement?
            kw["old_footprint"] = self.site.previous_source_footprints.pop(
                src.relpath, None
            )

        if date is None:
            date = self.site.localized_timestamp(src.stat.st_mtime)
        else:
            date = self.site.clean_date(date)

        # Skip draft pages
        if date > self.site.generation_time and not self.site.settings.DRAFT_MODE:
            log.info("%s: page is still a draft: skipping", src.relpath)
            return None

        try:
            return self._create_leaf_page(
                page_cls=page_cls, dst=dst, src=src, date=date, **kw
            )
        except SkipPage:
            return None

    def asset_child(self, name: str, src: file.File) -> SourceAssetNode:
        """
        Create the given child as a SourceNode
        """
        if (node := self.sub.get(name)) is not None:
            if not isinstance(node, SourceAssetNode):
                raise RuntimeError(
                    f"source node {name} already exists in {self.name}"
                    f" as {node.__class__.__name__} instead of SourceAssetNode {src.abspath}"
                )
            if src not in node.srcs:
                log.debug("assets: merging %s into %s", src.abspath, node)
                node.srcs.append(src)
            return node
        else:
            node = self.site.features.get_node_class(SourceAssetNode)(
                site=self.site, name=name, parent=self, src=src
            )
            self.sub[name] = node
            return node


class SourceAssetNode(SourceNode):
    """
    Node corresponding to a source directory that contains only asset pages
    """

    def __init__(self, site: Site, name: str, *, src: file.File, parent: Node):
        super().__init__(site, name, parent=parent)
        self.srcs: list[file.File] = [src]


class SourcePageNode(SourceNode):
    """
    Node corresponding to a source directory that contains non-asset pages
    """

    def __init__(self, site: Site, name: str, *, src: file.File, parent: Node | None):
        super().__init__(site, name, parent=parent)
        self.src: file.File = src

    def create_source_page_as_path(
        self,
        page_cls: type[P],
        src: file.File,
        name: str,
        date: datetime.datetime | None = None,
        **kw: Any,
    ) -> P | None:
        """
        Create a page of the given type, attaching it at the given path
        """
        if "created_from" in kw:
            raise RuntimeError("source page created with 'created_from' set")

        if self.site.last_load_step > self.site.LOAD_STEP_CONTENTS:
            raise RuntimeError(
                "Node.create_source_page created after the 'contents' step has completed"
            )

        if self.site.previous_source_footprints:
            # TODO: since we pop, we lose fooprint info for assets that replace other assets.
            # TODO: propagate it when doing the replacement?
            kw["old_footprint"] = self.site.previous_source_footprints.pop(
                src.relpath, None
            )

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
            return node._create_index_page(
                page_cls=page_cls, directory_index=False, src=src, date=date, **kw
            )
        except SkipPage:
            return None

    def create_source_page_as_index(
        self,
        page_cls: type[P],
        src: file.File,
        date: datetime.datetime | None = None,
        **kw: Any,
    ) -> P | None:
        """
        Create a page of the given type, attaching it at the given path
        """
        if "created_from" in kw:
            raise RuntimeError("source page created with 'created_from' set")

        if self.site.last_load_step > self.site.LOAD_STEP_CONTENTS:
            raise RuntimeError(
                "Node.create_source_page created after the 'contents' step has completed"
            )

        if self.site.previous_source_footprints:
            # TODO: since we pop, we lose fooprint info for assets that replace other assets.
            # TODO: propagate it when doing the replacement?
            kw["old_footprint"] = self.site.previous_source_footprints.pop(
                src.relpath, None
            )

        if date is None:
            date = self.site.localized_timestamp(src.stat.st_mtime)
        else:
            date = self.site.clean_date(date)

        # Skip draft pages
        if date > self.site.generation_time and not self.site.settings.DRAFT_MODE:
            log.info("%s: page is still a draft: skipping", src.relpath)
            return None

        try:
            return self._create_index_page(
                page_cls=page_cls, directory_index=True, src=src, date=date, **kw
            )
        except SkipPage:
            return None

    def page_child(self, name: str, src: file.File) -> SourcePageNode:
        """
        Create the given child as a SourceNode
        """
        if (node := self.sub.get(name)) is not None:
            if not isinstance(node, SourcePageNode):
                raise RuntimeError(
                    f"source node {name} already exists in {self.name}"
                    f" as {node.__class__.__name__} instead of source node {src.abspath}"
                )
            if node.src != src:
                raise RuntimeError(
                    f"source node {name} already exists in {self.name}"
                    f" as {node.src.abspath} instead of {src.abspath}"
                )
            return node

        node = self.site.features.get_node_class(SourcePageNode)(
            site=self.site, name=name, parent=self, src=src
        )
        self.sub[name] = node
        return node


class RootNode(SourcePageNode):
    """
    Node at the root of the site tree
    """

    title = fields.Str["Node"](
        doc="""
        Title used as site name.

        This only makes sense for the root node of the site hierarchy, and
        takes the value from the title of the root index page. If set, and the
        site name is not set by other means, it is used to give the site a name.
    """
    )

    def __init__(self, site: Site, *, src: file.File):
        super().__init__(site, name="", src=src, parent=None)

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

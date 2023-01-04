from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Generator, Optional, Sequence, TextIO, Type, TypeVar

from . import fields
from .site import SiteElement, Path

if TYPE_CHECKING:
    from .page import Page
    from .site import Site

log = logging.getLogger("node")

P = TypeVar("P", bound="Page")


class SkipPage(Exception):
    """
    Exception raised when a page should not be added to the site
    """
    pass


class Node(SiteElement):
    """
    One node in the rendered directory hierarchy of the site.

    Each node corresponds to a directory in the built site.

    Most nodes also correspond to directories in the source site, with the
    exceptions of nodes for autogenerated pages, and nodes for pages that will
    appear as paths (e.g.: `foo.md` builds as `foo/index.html`).
    """
    site_path = fields.Str["Node"](doc="""
        Where a content directory appears in the site.

        By default, is is the `site_path` of the parent directory, plus the directory
        name.

        If you are publishing the site at `/prefix` instead of the root of the domain,
        override this with `/prefix` in the content root.
    """)

    def __init__(
            self,
            site: Site,
            name: str, *,
            parent: Optional[Node] = None):
        super().__init__(site, parent=parent)
        # Basename of this node
        self.name: str = name
        # Path of this node from the root of the site (without leading /)
        self.path: str
        if parent is None:
            self.path = name
        else:
            self.path = os.path.join(parent.path, name)
        # Parent node, or None if this is the root
        self.parent: Optional[Node] = parent
        # Index page for this directory, if present
        self.page: Optional[Page] = None
        # SourcePages in this node indexed by source_name
        self.by_src_relpath: dict[str, Page] = {}
        # Pages to be rendered at this location
        self.build_pages: dict[str, Page] = {}
        # Subdirectories
        self.sub: dict[str, Node] = {}

    def __repr__(self) -> str:
        return f"Node({self.name})"

    def is_empty(self) -> bool:
        """
        Check if this node does not contain any content
        """
        if self.page is not None:
            return False
        if self.by_src_relpath:
            return False
        if self.build_pages:
            return False
        if self.sub:
            return False
        return True

    def prune_empty_subnodes(self) -> None:
        """
        Prune empty subnodes
        """
        empty: list[str] = []

        for name, node in self.sub.items():
            if node.is_empty():
                empty.append(name)

        # Remve empty subnodes
        for name in empty:
            del self.sub[name]

    def print(self, lead: str = "", file: Optional[TextIO] = None) -> None:
        if self.page:
            print(f"{lead}{self.name!r} page:{self.page!r}", file=file)
        else:
            print(f"{lead}{self.name!r} (no page)", file=file)
        for name, page in self.build_pages.items():
            print(f"{lead}- {name} → {page!r}", file=file)
        for name, node in self.sub.items():
            node.print(lead + "+ ", file=file)

    def iter_pages(self, prune: Sequence[Node] = (), source_only: bool = False) -> Generator[Page, None, None]:
        """
        Iterate all pages in this subtree
        """
        # Avoid nodes in prune
        if self in prune:
            return
        if source_only:
            yield from self.by_src_relpath.values()
        else:
            yield from self.build_pages.values()
        for node in self.sub.values():
            yield from node.iter_pages(prune, source_only=source_only)

    def lookup_page(self, path: Path) -> Optional[Page]:
        # print(f"Node.lookup_page: {self.name=!r}, {self.page=!r}, {path=!r},"
        #       f" sub={self.sub.keys() if self.sub else 'None'}")

        if not path:
            return self.page

        if path.head == "..":
            if self.parent is None:
                return None
            return self.parent.lookup_page(path.tail)
        elif path.head in (".", ""):
            # Probably not worth trying to avoid a recursion step here, since
            # this should not be a common occurrence
            return self.lookup_page(path.tail)

        if len(path) > 1:
            if not self.sub:
                return None
            elif (subnode := self.sub.get(path.head)):
                # print(f"Node.lookup_page:  descend into {subnode.name!r} with {path.tail=!r}")
                return subnode.lookup_page(path.tail)
            else:
                return None

        # Match subnode name
        if (subnode := self.sub.get(path.head)) and subnode.page:
            return subnode.page

        # Match subpage names and basename of src.relpath in subpages
        if (page := self.build_pages.get(path.head)) is not None:
            return page
        if (page := self.by_src_relpath.get(path.head)) is not None:
            return page

        return None

    def create_auto_page_as_file(
            self, *,
            page_cls: Type[P],
            dst: str,
            **kw: Any) -> Optional[P]:
        """
        Create a page of the given type, attaching it at the given path
        """
        if "src" in kw:
            raise RuntimeError("auto page created with 'src' set")

        if self.site.last_load_step != self.site.LOAD_STEP_ORGANIZE:
            raise RuntimeError("Node.create_auto_page created outside the 'generate' step")

        try:
            if dst:
                return self._create_leaf_page(page_cls=page_cls, dst=dst, **kw)
            else:
                return self._create_index_page(page_cls=page_cls, directory_index=False,  **kw)
        except SkipPage:
            return None

    def create_auto_page_as_path(
            self,
            page_cls: Type[P],
            name: str,
            **kw: Any) -> Optional[P]:
        """
        Create a page of the given type, attaching it at the given path
        """
        if "src" in kw:
            raise RuntimeError("auto page created with 'src' set")

        if self.site.last_load_step != self.site.LOAD_STEP_ORGANIZE:
            raise RuntimeError("Node.create_auto_page created outside the 'generate' step")

        node = self._child(name)

        try:
            return node._create_index_page(page_cls=page_cls, directory_index=False,  **kw)
        except SkipPage:
            return None

    def create_auto_page_as_index(
            self,
            page_cls: Type[P],
            **kw: Any) -> Optional[P]:
        """
        Create a page of the given type, attaching it at the given path
        """
        if "src" in kw:
            raise RuntimeError("auto page created with 'src' set")

        if self.site.last_load_step != self.site.LOAD_STEP_ORGANIZE:
            raise RuntimeError("Node.create_auto_page created outside the 'generate' step")

        try:
            return self._create_index_page(page_cls=page_cls, directory_index=True, **kw)
        except SkipPage:
            return None

    def _create_index_page(
            self, *,
            page_cls: Type[P],
            directory_index: bool = False,
            **kw: Any) -> P:
        from .page import PageValidationError
        from .asset import Asset

        if directory_index:
            search_root_node = self
        elif self.parent is not None:
            search_root_node = self.parent
        else:
            search_root_node = self

        # Create the page
        try:
            page = self.site.features.get_page_class(page_cls)(
                site=self.site, dst="index.html", node=self,
                search_root_node=search_root_node,
                leaf=False,
                directory_index=directory_index, **kw)
        except PageValidationError as e:
            log.warn("%s: skipping page: %s", e.page, e.msg)
            raise SkipPage()

        if self.page is not None:
            if isinstance(self.page, Asset) and isinstance(page, Asset):
                # Allow replacement of assets
                page.old_footprint = self.page.old_footprint
            else:
                log.warn("%s: page %r attempts to replace page %r: skipped", self.path, page, self.page)
                raise SkipPage()

        self.page = page
        if page.source_name is not None:
            search_root_node.by_src_relpath[page.source_name] = page
        self.build_pages["index.html"] = page
        # if page.directory_index is False:
        #     print(f"{page=!r} dst is not set but page is not a directory index")
        return page

    def _create_leaf_page(
            self, *,
            page_cls: Type[P],
            dst: str,
            **kw: Any) -> P:
        from .page import PageValidationError
        from .asset import Asset

        # Create the page
        try:
            page = self.site.features.get_page_class(page_cls)(
                site=self.site, dst=dst,
                node=self,
                search_root_node=self,
                leaf=True,
                directory_index=False, **kw)
        except PageValidationError as e:
            log.warn("%s: skipping page: %s", e.page, e.msg)
            raise SkipPage()

        if (old := self.build_pages.get(dst)):
            if isinstance(old, Asset) and isinstance(page, Asset):
                # Allow replacement of assets
                page.old_footprint = old.old_footprint
            else:
                log.warn("%s: page %r attempts to replace page %r: skipped", self.path, page, self.page)
                raise SkipPage()

        self.build_pages[dst] = page
        if page.source_name is not None:
            self.by_src_relpath[page.source_name] = page
        return page

    def _child(self, name: str) -> Node:
        """
        Return the given subnode, creating it if missing
        """
        if (node := self.sub.get(name)):
            return node

        node = self.site.features.get_node_class(Node)(site=self.site, name=name, parent=self)
        self.sub[name] = node
        return node

    def lookup_node(self, path: Path) -> Optional[Node]:
        """
        Return the subnode at the given relative path, or None if it does not
        exist.

        Path elements of "." and ".." are supported
        """
        if not path:
            return self
        if path.head == ".":
            # Probably not worth trying to avoid a recursion step here, since
            # this should not be a common occurrence
            return self.lookup_node(path.tail)
        elif path.head == "..":
            if self.parent is None:
                return None
            else:
                return self.parent.lookup_node(path.tail)
        elif (sub := self.sub.get(path.head)):
            return sub.lookup_node(path.tail)
        return None

    def contains(self, page: Page) -> bool:
        """
        Check if page is contained in or under this node
        """
        # Walk the parent chain of page.node to see if we find self
        node: Optional[Node] = page.node
        while node is not None:
            if node == self:
                return True
            node = node.parent
        return False

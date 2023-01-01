from __future__ import annotations
from typing import TYPE_CHECKING, Tuple, Optional, Union
import os
import locale
import mimetypes
import logging

if TYPE_CHECKING:
    from staticsite.site import Site
    from staticsite.page import Page
    from staticsite.node import Node

log = logging.getLogger("serve")


class PageFS:
    """
    VFS-like abstraction that maps the names of files that pages would render
    with the corresponding pages.

    This can be used to render pages on demand.
    """
    def __init__(self, site: Site):
        self.paths: dict[str, Page] = {}
        self.add_tree(site.root)

    def add_tree(self, root: Node, relpath: str = ""):
        for name, page in root.build_pages.items():
            self.paths[os.path.join(relpath, name)] = page

        for name, sub in root.sub.items():
            self.add_tree(sub, os.path.join(relpath, name))

    def get_page(self, relpath: str) -> Union[tuple[None, None], tuple[str, Page]]:
        if not relpath:
            relpath = "/index.html"
        dst_relpath = os.path.normpath(relpath).lstrip("/")
        page = self.paths.get(dst_relpath, None)
        if page is not None:
            return dst_relpath, page

        dst_relpath = os.path.join(dst_relpath, "index.html")
        page = self.paths.get(dst_relpath, None)
        if page is not None:
            return dst_relpath, page

        return None, None

    def render(self, path, **kw) -> Tuple[Optional[str], Optional[bytes]]:
        """
        Find the page for the given path and return its rendered contents
        """
        dst_relpath, page = self.get_page(os.path.normpath(path).lstrip("/"))
        if page is None:
            return None, None

        # Set locale for rendering
        try:
            lname = page.site.settings.LANGUAGES[0]["locale"]
            locale.setlocale(locale.LC_ALL, lname)
        except locale.Error as e:
            log.warn("%s: cannot set locale to %s: %s", page, lname, e)

        rendered = page.render(**kw)
        build_path = os.path.join(page.node.path, page.dst)
        return build_path, rendered.content()

    def serve_path(self, path, environ, start_response):
        """
        Render a page on the fly and serve it.

        Call start_response with the page headers and return the bytes() with
        the page contents.

        start_response is the start_response from WSGI

        Returns None without calling start_response if no page was found.
        """
        relpath, content = self.render(path)
        start_response("200 OK", [
            ("Content-Type", mimetypes.guess_type(relpath)[0]),
            ("Content-Length", str(len(content))),
        ])
        return [content]

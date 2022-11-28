from __future__ import annotations
from typing import TYPE_CHECKING, Tuple, Optional
import os
import locale
import mimetypes
import logging

if TYPE_CHECKING:
    from staticsite.site import Site
    from staticsite.page import Page

log = logging.getLogger("serve")


class PageFS:
    """
    VFS-like abstraction that maps the names of files that pages would render
    with the corresponding pages.

    This can be used to render pages on demand.
    """
    def __init__(self, site: Site = None):
        self.paths = {}

        if site:
            for page in site.structure.pages.values():
                for build_path in page.target_relpaths():
                    self.add_page(page, build_path)

    def add_page(self, page: Page, build_path: str = None):
        if build_path is None:
            build_path = page.meta["build_path"]
        self.paths[build_path] = page

    def get_page(self, relpath: str) -> Tuple[str, Page]:
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
        return page.meta["build_path"], rendered.content()

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

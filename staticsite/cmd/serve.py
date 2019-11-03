from .command import SiteCommand
import os
import sys
import mimetypes
import gc
import logging

log = logging.getLogger()


class PageFS:
    """
    VFS-like abstraction that maps the names of files that pages would render
    with the corresponding pages.

    This can be used to render pages on demand.
    """
    def __init__(self):
        self.paths = {}

    def add_site(self, site):
        for page in site.pages.values():
            for relpath in page.target_relpaths():
                self.add_page(page, relpath)

    def add_page(self, page, dst_relpath=None):
        if dst_relpath is None:
            dst_relpath = page.dst_relpath
        self.paths[dst_relpath] = page

    def get_page(self, relpath):
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

    def serve_path(self, path, environ, start_response):
        """
        Render a page on the fly and serve it.

        Call start_response with the page headers and return the bytes() with
        the page contents.

        start_response is the start_response from WSGI

        Returns None without calling start_response if no page was found.
        """
        dst_relpath, page = self.get_page(os.path.normpath(path).lstrip("/"))
        if page is None:
            return None

        for relpath, rendered in page.render().items():
            if relpath == dst_relpath:
                break
        else:
            return None

        content = rendered.content()
        start_response("200 OK", [
            ("Content-Type", mimetypes.guess_type(relpath)[0]),
            ("Content-Length", str(len(content))),
        ])
        return [content]


class Serve(SiteCommand):
    "serve the site over HTTP, building it in memory on demand"

    def run(self):
        mimetypes.init()

        site = self.reload()

        try:
            from livereload import Server
        except ImportError:
            print("Please install the python3 livereload module to use this function.", file=sys.stderr)
            return
        server = Server(self.application)

        # see https://github.com/lepture/python-livereload/issues/171
        def do_reload():
            self.reload()
        content_root = os.path.join(site.settings.PROJECT_ROOT, site.settings.CONTENT)
        server.watch(content_root, do_reload)
        server.watch(site.theme.root, do_reload)
        server.serve(port=8000, host="localhost")

    def application(self, environ, start_response):
        path = environ.get("PATH_INFO", None)
        if path is None:
            start_response("404 not found", [("Content-Type", "text/plain")])
            return [b"Not found"]

        content = self.pages.serve_path(path, environ, start_response)
        if content is not None:
            return content

        start_response("404 not found", [("Content-Type", "text/plain")])
        return [b"Not found"]

    def reload(self):
        log.info("Loading site")
        site = self.load_site()
        self.pages = PageFS()
        self.pages.add_site(site)
        gc.collect()
        return site

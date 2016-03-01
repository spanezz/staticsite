# coding: utf-8

from .commands import SiteCommand, CmdlineError
from staticsite.core import settings
import os
import mimetypes
import gc
import logging

log = logging.getLogger()

class Serve(SiteCommand):
    "serve the site over HTTP, building it in memory on demand"

    def run(self):
        mimetypes.init()

        self.reload()

        from livereload import Server
        server = Server(self.application)
        server.watch(os.path.join(self.root, "site"), self.reload)
        server.watch(os.path.join(self.root, "theme"), self.reload)
        server.serve(port=8000, host="localhost")

    def application(self, environ, start_response):
        path = environ.get("PATH_INFO", None)
        if path is None:
            start_response("404 not found", [("Content-Type", "text/plain")])
            return [b"Not found"]

        normrelpath, page = self.resolve_path(path)
        if page is not None:
            for relpath, rendered in page.render().items():
                relpath = os.path.normpath(os.path.join("/", relpath))
                if relpath == normrelpath:
                    start_response("200 OK", [("Content-Type", mimetypes.guess_type(relpath)[0])])
                    return [rendered.content()]

        start_response("404 not found", [("Content-Type", "text/plain")])
        return [b"Not found"]

    def resolve_path(self, path):
        """
        Return normpath(relpath) from the page found and the page found
        """
        path = os.path.normpath(path)
        page = self.url_map.get(path, None)
        if page is not None:
            return path, page

        path = os.path.join(path, "index.html")
        page = self.url_map.get(path, None)
        if page is not None:
            return path, page

        return None, None

    def reload(self):
        log.info("Loading site")
        self.site = self.load_site()
        gc.collect()

        self.url_map = {}
        for page in self.site.pages.values():
            for relpath in page.target_relpaths():
                relpath = os.path.normpath(os.path.join("/", relpath))
                self.url_map[relpath] = page

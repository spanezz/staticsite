# coding: utf-8

from .commands import SiteCommand, CmdlineError
from staticsite.core import PageFS
import os
import sys
import mimetypes
import gc
import logging

log = logging.getLogger()

class Serve(SiteCommand):
    "serve the site over HTTP, building it in memory on demand"

    def run(self):
        mimetypes.init()

        self.reload()

        try:
            from livereload import Server
        except ImportError:
            print("Please install the python3 livereload module to use this function.", file=sys.stderr)
            return
        server = Server(self.application)
        server.watch(self.content_root, self.reload)
        server.watch(self.theme_root, self.reload)
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
        self.site = self.load_site()
        gc.collect()

        self.pages = PageFS()
        self.pages.add_site(self.site)

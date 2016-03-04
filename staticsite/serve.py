# coding: utf-8

from .commands import SiteCommand, CmdlineError
from staticsite.core import settings, PageFS
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

        dst_relpath, page = self.pages.get_page(os.path.normpath(path).lstrip("/"))
        if page is not None:
            for relpath, rendered in page.render().items():
                if relpath == dst_relpath:
                    start_response("200 OK", [("Content-Type", mimetypes.guess_type(relpath)[0])])
                    return [rendered.content()]

        start_response("404 not found", [("Content-Type", "text/plain")])
        return [b"Not found"]

    def reload(self):
        log.info("Loading site")
        self.site = self.load_site()
        gc.collect()

        self.pages = PageFS()
        for page in self.site.pages.values():
            for relpath in page.target_relpaths():
                self.pages.add_page(page, relpath)

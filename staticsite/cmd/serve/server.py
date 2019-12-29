from __future__ import annotations
from typing import TYPE_CHECKING
import gc
import mimetypes
import tornado.web
from tornado.web import url
import tornado.httpserver
import tornado.netutil
import tornado.ioloop
from staticsite import Site
from staticsite.utils import timings
from .pagefs import PageFS

if TYPE_CHECKING:
    from staticsite.settings import Settings


class ServePage(tornado.web.RequestHandler):
    def get(self):
        relpath, content = self.application.pages.render(self.request.path)
        if relpath is None:
            self.send_error(404)
        else:
            self.set_header("Content-Type", mimetypes.guess_type(relpath)[0])
            self.finish(content)


class Application(tornado.web.Application):
    def __init__(self, settings: Settings):
        mimetypes.init()

        urls = [
            url(r".*", ServePage, name="page"),
        ]

        super().__init__(
            urls,
            xsrf_cookies=True,
        )

        self.site_settings = settings
        self.site = None
        self.pages = None

    def reload(self):
        # (re)instantiate site
        self.site = Site(settings=self.site_settings)
        with timings("Loaded site in %fs"):
            self.site.load()
        with timings("Analysed site tree in %fs"):
            self.site.analyze()
        self.pages = PageFS(self.site)
        gc.collect()

from __future__ import annotations
from ..command import Command, SiteCommand
import tornado.httpserver
import tornado.netutil
from .pagefs import PageFS
import os
import asyncio
import webbrowser
import logging

log = logging.getLogger("serve")


class ServerMixin:
    def start_server(self):
        from .server import Application
        app = Application(self.settings)
        app.reload()

        sockets = tornado.netutil.bind_sockets(self.args.port, self.args.host)
        pairs = []
        for s in sockets:
            pairs.append(s.getsockname()[:2])
        pairs.sort()
        host, port = pairs[0]

        if ":" in host:
            host = f"[{host}]"
        url = f"http://{host}:{port}"
        log.info("Serving on %s", url)

        if self.settings.SITE_URL is None:
            self.settings.SITE_URL = url

        server = tornado.httpserver.HTTPServer(app)
        server.add_sockets(sockets)

        async def open_browser():
            webbrowser.open_new_tab(url)

        if not getattr(self.args, "no_start", True):
            tornado.ioloop.IOLoop.current().add_callback(open_browser)
        else:
            print(url)

        loop = asyncio.get_event_loop()
        loop.run_forever()

#    def make_server(self, watch_paths=[]):
#        try:
#            import livereload
#        except ImportError:
#            raise Fail("Please install the python3 livereload module to use this function.")
#
#        class Server(livereload.Server):
#            def _setup_logging(self):
#                # Keep existing logging setup
#                pass
#
#        server = Server(self.application)
#
#        # see https://github.com/lepture/python-livereload/issues/171
#        def do_reload():
#            self.reload()
#
#        for path in watch_paths:
#            log.info("watching changes on %s", path)
#            server.watch(path, do_reload)
#
#        return server

    def run(self):
        self.start_server()


class Serve(ServerMixin, SiteCommand):
    "Serve the site over HTTP, building it in memory on demand"

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("--port", "-p", action="store", type=int, default=8000,
                            help="port to use (default: 8000)")
        parser.add_argument("--host", action="store", type=str, default="localhost",
                            help="host to bind to (default: localhost)")
        return parser


class Show(ServerMixin, Command):
    "Show the current directory in a browser"

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        # Set default project root if undefined
        self.settings.PROJECT_ROOT = self.args.dir
        if self.settings.PROJECT_ROOT is None:
            self.settings.PROJECT_ROOT = os.getcwd()

        # Command line overrides for settings
        if self.args.theme:
            self.settings.THEME = (os.path.abspath(self.args.theme),)
        if self.args.draft:
            self.settings.DRAFT_MODE = True

        # Do not clutter previewed directories with .staticsite-cache directories
        self.settings.CACHE_REBUILDS = False

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)

        parser.add_argument("dir", nargs="?",
                            help="directory to show (default: the current directory)")
        parser.add_argument("--theme", help="theme directory location. Overrides settings.THEME")
        parser.add_argument("--draft", action="store_true", help="do not ignore pages with date in the future")
        parser.add_argument("--no-start", "-n", action="store_true",
                            help="do not start a browser automatically, print the URL instead")
        parser.add_argument("--port", "-p", action="store", type=int, default=0,
                            help="port to use (default: randomly allocated)")
        parser.add_argument("--host", action="store", type=str, default="localhost",
                            help="host to bind to (default: localhost)")
        return parser

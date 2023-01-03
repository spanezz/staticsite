from __future__ import annotations

import argparse
import logging
import os
from typing import Any

from ..command import Command, Fail, SiteCommand, register

log = logging.getLogger("serve")


class ServerMixin(Command):
    def start_server(self) -> None:
        try:
            import tornado.httpserver
            import tornado.netutil
        except ModuleNotFoundError:
            raise Fail("python3-tornado is not installed")
        import asyncio
        import webbrowser

        from .server import Application

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

        if not hasattr(self.settings, "SITE_URL"):
            self.settings.SITE_URL = url

        app = Application(self.settings)
        app.reload()

        server = tornado.httpserver.HTTPServer(app)
        server.add_sockets(sockets)

        async def open_browser() -> None:
            webbrowser.open_new_tab(url)

        if not getattr(self.args, "no_start", True):
            tornado.ioloop.IOLoop.current().add_callback(open_browser)
        else:
            print(url)

        loop = asyncio.get_event_loop()
        loop.run_forever()

    def run(self) -> None:
        self.start_server()


@register
class Serve(ServerMixin, SiteCommand):
    "Serve the site over HTTP, building it in memory on demand"

    @classmethod
    def add_subparser(cls, subparsers: "argparse._SubParsersAction[Any]") -> argparse.ArgumentParser:
        parser = super().add_subparser(subparsers)
        parser.add_argument("--port", "-p", action="store", type=int, default=8000,
                            help="port to use (default: 8000)")
        parser.add_argument("--host", action="store", type=str, default="localhost",
                            help="host to bind to (default: localhost)")
        return parser


@register
class Show(ServerMixin, Command):
    "Show the current directory in a browser"

    def __init__(self, *args: Any, **kw: Any) -> None:
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
    def add_subparser(cls, subparsers: "argparse._SubParsersAction[Any]") -> argparse.ArgumentParser:
        parser = super().add_subparser(subparsers)

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

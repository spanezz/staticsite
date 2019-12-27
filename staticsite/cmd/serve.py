from .command import Command, SiteCommand, Fail
import os
import mimetypes
import gc
import locale
import logging

log = logging.getLogger("serve")


class PageFS:
    """
    VFS-like abstraction that maps the names of files that pages would render
    with the corresponding pages.

    This can be used to render pages on demand.
    """
    def __init__(self):
        self.paths = {}

    def set_site(self, site):
        for page in site.pages.values():
            for build_path in page.target_relpaths():
                self.add_page(page, build_path)

    def add_page(self, page, build_path=None):
        if build_path is None:
            build_path = page.meta["build_path"]
        self.paths[build_path] = page

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

        # Set locale for rendering
        try:
            lname = page.site.settings.LANGUAGES[0]["locale"]
            locale.setlocale(locale.LC_ALL, lname)
        except locale.Error as e:
            log.warn("%s: cannot set locale to %s: %s", page, lname, e)

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


class ServerMixin:
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.pages = PageFS()
        mimetypes.init()

        # Do not clutter previewed directories with .staticsite-cache directories
        self.settings.CACHE_REBUILDS = False

    def make_server(self, watch_paths=[]):
        try:
            import livereload
        except ImportError:
            raise Fail("Please install the python3 livereload module to use this function.")

        class Server(livereload.Server):
            def _setup_logging(self):
                # Keep existing logging setup
                pass

        server = Server(self.application)

        # see https://github.com/lepture/python-livereload/issues/171
        def do_reload():
            self.reload()

        for path in watch_paths:
            log.info("watching changes on %s", path)
            server.watch(path, do_reload)

        return server

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
        self.pages.set_site(site)
        gc.collect()
        return site

    def get_source_dirs(self, site):
        dirs = list(site.theme.feature_dirs) + list(site.theme.template_lookup_paths)
        for name in site.theme.system_assets:
            dirs.append(os.path.join("/usr/share/javascript", name))
        return dirs


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

    def run(self):
        if self.settings.SITE_URL is None:
            self.settings.SITE_URL = f"http://{self.args.host}:{self.args.port}"
        site = self.reload()
        server = self.make_server(self.get_source_dirs(site))
        server.serve(port=self.args.port, host=self.args.host)


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

    def run(self):
        site = self.reload()
        server = self.make_server(self.get_source_dirs(site))
        arg_no_start = self.args.no_start
        arg_port = self.args.port
        arg_host = self.args.host

        import tornado.web
        import tornado.httpserver
        import tornado.netutil
        import tornado.ioloop
        import webbrowser

        class Application(tornado.web.Application):
            def listen(self, *args, **kw):
                sockets = tornado.netutil.bind_sockets(arg_port, arg_host)
                server = tornado.httpserver.HTTPServer(self)
                server.add_sockets(sockets)
                pairs = []
                for s in sockets:
                    pairs.append(s.getsockname()[:2])
                pairs.sort()
                host, port = pairs[0]
                if ":" in host:
                    host = f"[{host}]"
                url = f"http://{host}:{port}"
                log.info("Actually serving on %s", url)

                async def open_browser():
                    webbrowser.open_new_tab(url)

                if not arg_no_start:
                    tornado.ioloop.IOLoop.current().add_callback(open_browser)
                else:
                    print(url)
                return server

        # Monkey patch to be able to start servers in a smoother way that the
        # defaults of livereload
        import livereload.server
        livereload.server.web.Application = Application
        server.serve()

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

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict
import os
import gc
import mimetypes
import asyncio
import logging
import json
import pyinotify
import tornado.web
from tornado.web import url
import tornado.httpserver
import tornado.netutil
import tornado.websocket
import tornado.ioloop
from staticsite.site import Site
from staticsite.utils import timings
from .pagefs import PageFS

if TYPE_CHECKING:
    from staticsite.settings import Settings


log = logging.getLogger("serve")


class ChangeMonitor:
    """
    Trigger an event when a file is removed, then recreate the file
    """
    def __init__(self, app: "Application"):
        self.app = app
        self.loop = asyncio.get_event_loop()
        # Set up pyinotify.
        # See https://stackoverflow.com/questions/26414052/watch-for-a-file-with-asyncio
        self.watch_manager = pyinotify.WatchManager()
        # Map absolute paths to Watch handlers
        self.watches: Dict[str, pyinotify.Watch] = {}
        # self.watch = self.watch_manager.add_watch(self.media_dir, pyinotify.IN_DELETE)
        self.notifier = pyinotify.AsyncioNotifier(
                self.watch_manager, self.loop, default_proc_fun=self.on_event)
        # Pending trigger
        self.pending = None

    def update_watch_dirs(self, dirs: List[str]):
        dirs = [os.path.realpath(d) for d in dirs]

        for path in self.watches.keys() - dirs:
            watch = self.watches.pop(path)
            self.watch_manager.rm_watch(watch)
            log.info("%s: removing watch", path)

        for path in set(dirs) - self.watches.keys():
            self.watches[path] = self.watch_manager.add_watch(
                    path, pyinotify.IN_CLOSE_WRITE | pyinotify.IN_DELETE, rec=True)
            log.info("%s: adding watch", path)

    def notify(self):
        self.pending = None
        self.app.trigger_reload()

    def on_event(self, event):
        """
        Handle incoming asyncio events
        """
        if event.name.startswith(".") and event.name != ".staticsite":
            return

        if os.path.basename(event.path).startswith("."):
            return

        # Check that it's not an event from inside a hidden directory like
        # .staticsite-cache
        event_path = os.path.realpath(event.path)
        for path in self.watches.keys():
            if event_path == path:
                break
            if event_path.startswith(path):
                relpath = os.path.relpath(event_path, path)
                while relpath:
                    dirname, basename = os.path.split(relpath)
                    if basename.startswith("."):
                        return
                    relpath = dirname
                break
        else:
            # Event not for a path that we watch
            return

        log.debug("Received event %r", event)

        # Introduce a delay of 0.1s from the last event received, to notify
        # only once in case of a burst of events
        if self.pending is not None:
            self.pending.cancel()
            self.pending = None
        self.pending = self.loop.call_later(0.1, self.notify)


class PageSocket(tornado.websocket.WebSocketHandler):
    def open(self):
        log.debug("WebSocket connection opened")
        self.application.add_page_socket(self)

    def on_message(self, message):
        log.debug("WebSocket message received: %r", message)

    def on_close(self):
        log.debug("WebSocket connection closed")
        self.application.remove_page_socket(self)


class ServePage(tornado.web.RequestHandler):
    def get(self):
        if self.request.protocol == "http":
            self.ws_url = "ws://" + self.request.host + \
                          self.application.reverse_url("page_socket")
        else:
            self.ws_url = "wss://" + self.request.host + \
                          self.application.reverse_url("page_socket")

        relpath, content = self.application.pages.render(self.request.path, server=self.application, handler=self)
        if relpath is None:
            self.send_error(404)
        else:
            self.set_header("Content-Type", mimetypes.guess_type(relpath)[0])
            self.finish(content)


class Application(tornado.web.Application):
    def __init__(self, settings: Settings):
        mimetypes.init()

        urls = [
            url(r"/_server/websocket", PageSocket, name="page_socket"),
            url(r".*", ServePage, name="page"),
        ]

        super().__init__(
            urls,
            xsrf_cookies=True,
        )

        self.site_settings: Settings = settings
        self.site: Site
        self.pages: PageFS
        self.page_sockets: set[PageSocket] = set()
        self.change_monitor = ChangeMonitor(self)

    def add_page_socket(self, handler):
        self.page_sockets.add(handler)

    def remove_page_socket(self, handler):
        self.page_sockets.discard(handler)

    def trigger_reload(self):
        log.info("Content change detected: reloading site")
        self.reload()
        payload = json.dumps({"event": "reload"})
        for handler in self.page_sockets:
            handler.write_message(payload)

    def reload(self):
        # (re)instantiate site
        # FIXME: do the build in a thread worker?
        self.site = Site(settings=self.site_settings)
        with timings("Loaded site in %fs"):
            self.site.load()

        self.change_monitor.update_watch_dirs(self.get_source_dirs())

        self.pages = PageFS(self.site)
        gc.collect()

    def get_source_dirs(self) -> List[str]:
        """
        Get the directories used as sources to the site
        """
        # TODO: reload when source changes
        # See /usr/lib/python3/dist-packages/tornado/autoreload.py:_reload_on_update
        # for example code on how to list source files for the running program
        dirs = [self.site.content_root]
        dirs.extend(self.site.theme.feature_dirs)
        dirs.extend(self.site.theme.template_lookup_paths)
        for name in self.site.theme.system_assets:
            dirs.append(os.path.join("/usr/share/javascript", name))
        return dirs

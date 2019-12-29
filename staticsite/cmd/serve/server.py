from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict
import os
import gc
import mimetypes
import asyncio
import logging
import pyinotify
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
        for path in self.watches.keys() - dirs:
            watch = self.watches.pop(path)
            self.watch_manager.rm_watch(watch)

        for path in set(dirs) - self.watches.keys():
            self.watches[path] = self.watch_manager.add_watch(path, pyinotify.IN_CLOSE_WRITE | pyinotify.IN_DELETE)

    def notify(self):
        self.pending = None
        self.app.trigger_reload()

    def on_event(self, event):
        """
        Handle incoming asyncio events
        """
        # Introduce a delay of 0.1s from the last event received, to notify
        # only once in case of a burst of events
        if self.pending is not None:
            self.pending.cancel()
            self.pending = None
        self.pending = self.loop.call_later(0.1, self.notify)


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
        self.change_monitor = ChangeMonitor(self)

    def trigger_reload(self):
        log.info("Content change detected: reloading site")
        self.reload()

    def reload(self):
        # (re)instantiate site
        # FIXME: do the build in a thread worker?
        self.site = Site(settings=self.site_settings)
        with timings("Loaded site in %fs"):
            self.site.load()
        with timings("Analysed site tree in %fs"):
            self.site.analyze()

        self.change_monitor.update_watch_dirs(self.get_source_dirs())

        self.pages = PageFS(self.site)
        gc.collect()

    def get_source_dirs(self) -> List[str]:
        """
        Get the directories used as sources to the site
        """
        dirs = list(self.site.theme.feature_dirs) + list(self.site.theme.template_lookup_paths)
        for name in self.site.theme.system_assets:
            dirs.append(os.path.join("/usr/share/javascript", name))
        return dirs

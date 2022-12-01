from __future__ import annotations

import contextlib
import locale
import logging
import os
import shutil
import time
from collections import Counter
from typing import TYPE_CHECKING, Generator

from .. import structure, utils
from .command import Fail, SiteCommand

if TYPE_CHECKING:
    from ..page import Page

log = logging.getLogger("build")


class Build(SiteCommand):
    "build the site into the web/ directory of the project"

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def run(self):
        self.site = self.load_site()
        self.builder = Builder(self.site)
        self.builder.write()


class RenderStats:
    def __init__(self):
        self.sums = Counter()
        self.counts = Counter()

    @contextlib.contextmanager
    def collect(self, page: Page):
        start = time.perf_counter_ns()
        yield
        end = time.perf_counter_ns()
        self.sums[page.TYPE] += end - start
        self.counts[page.TYPE] += 1


class RenderDirectory:
    """
    A directory where contents are being rendered
    """
    def __init__(self, root: str, relpath: str, dir_fd: int):
        self.root = root
        self.relpath = relpath
        self.dir_fd = dir_fd

        # Scan directory contents
        # TODO: do also stat() to be able to skip rendering of needed
        self.old_dirs: set[str] = set()
        self.old_files: set[str] = set()
        with os.scandir(dir_fd) as entries:
            for de in entries:
                if de.is_dir():
                    self.old_dirs.add(de.name)
                else:
                    self.old_files.add(de.name)

    @classmethod
    @contextlib.contextmanager
    def open(cls, root: str) -> Generator[RenderDirectory, None, None]:
        """
        Start rendering in the given output root directory
        """
        os.makedirs(root, exist_ok=True)
        with utils.open_dir_fd(root) as dir_fd:
            yield cls(root, "", dir_fd)

    @contextlib.contextmanager
    def subdir(self, name: str) -> Generator[RenderDirectory, None, None]:
        subpath = os.path.join(self.relpath, name)
        with utils.open_dir_fd(name, dir_fd=self.dir_fd) as subdir_fd:
            yield RenderDirectory(self.root, subpath, subdir_fd)

    def prepare_subdir(self, name: str):
        """
        Prepare for rendering a subdirectory
        """
        if name in self.old_dirs:
            # Directory already existed: reuse it
            self.old_dirs.discard(name)
        elif name in self.old_files:
            # There was a file at this location: delete it
            self.old_files.discard(name)
            os.unlink(name, dir_fd=self.dir_fd)
            os.mkdir(name, dir_fd=self.dir_fd)
        else:
            # There was nothing: create the directory
            os.mkdir(name, dir_fd=self.dir_fd)

    def prepare_file(self, name: str):
        """
        Prepare for rendering a file
        """
        if name in self.old_dirs:
            # There is a directory instead: remove it
            self.old_dirs.discard(name)
            # FIXME: from Python 3.11, rmtree supports dir_fd
            shutil.rmtree(os.path.join(self.root, self.relpath, name))
        elif name in self.old_files:
            # There is a file at this location: it will be overwritten
            self.old_files.discard(name)

    def cleanup_leftovers(self):
        """
        Remove previously existing files and directories that have disappeared
        in the current version of the site
        """
        for name in self.old_dirs:
            # FIXME: from Python 3.11, rmtree supports dir_fd
            shutil.rmtree(os.path.join(self.root, self.relpath, name))
        for name in self.old_files:
            os.unlink(name, dir_fd=self.dir_fd)


class Builder:
    def __init__(self, site):
        self.site = site
        if self.site.settings.OUTPUT is None:
            raise Fail(
                    "No output directory configured:"
                    " please use --output or set OUTPUT in settings.py or .staticsite.py")
        self.build_root = os.path.join(site.settings.PROJECT_ROOT, site.settings.OUTPUT)
        # Logs which pages have been rendered and to which path
        self.build_log: dict[str, Page] = {}

    def write(self):
        """
        Generate output
        """
        # Set locale for rendering
        try:
            lname = self.site.settings.LANGUAGES[0]["locale"]
            locale.setlocale(locale.LC_ALL, lname)
        except locale.Error as e:
            log.warn("Cannot set locale to %s: %s", lname, e)

        with utils.timings("Built site in %fs"):
            # cpu_count = os.cpu_count()
            # if cpu_count > 1:
            #     self.write_multi_process(cpu_count)
            # else:
            #     self.write_single_process()

            # I tried trivial parallelisation with child processes but the benefits
            # do not seem significant:
            #
            #     real  0m5.111s
            #     user  0m8.096s
            #     sys   0m0.644s
            #
            # compared with:
            #
            #     real  0m6.251s
            #     user  0m5.760s
            #     sys   0m0.468s
            self.write_single_process()

#     def write_multi_process(self, child_count):
#         log.info("Generating pages using %d child processes", child_count)
#
#         pages = list(self.site.structure.pages.values())
#
#         # From http://code.activestate.com/recipes/576785-partition-an-iterable-into-n-lists/
#         chunks = [pages[i::child_count] for i in range(child_count)]
#
#         print(len(pages))
#         for c in chunks:
#             print(len(c))
#
#         import sys
#         pids = set()
#         for chunk in chunks:
#             pid = os.fork()
#             if pid == 0:
#                 self.write_pages(chunk)
#                 sys.exit(0)
#             else:
#                 pids.add(pid)
#
#         while pids:
#             (pid, status) = os.wait()
#             pids.discard(pid)

    def write_single_process(self):
        stats = RenderStats()
        os.makedirs(self.build_root, exist_ok=True)
        with RenderDirectory.open(self.build_root) as render_dir:
            self.write_subtree(self.site.structure.root, render_dir, stats=stats)
        for type in sorted(stats.sums.keys()):
            log.info("%s: %d in %.3fs (%.1f per minute)",
                     type,
                     stats.counts[type],
                     stats.sums[type] / 1_000_000_000,
                     stats.counts[type] / stats.sums[type] * 60 / 1_000_000_000)

    def write_subtree(self, node: structure.Node, render_dir: RenderDirectory, stats: RenderStats):
        """
        Recursively render the given node in the given render directory
        """
        # If this is the build node for a page, render it
        if node.page and node == node.page.build_node:
            render_dir.prepare_file(node.name)
            with stats.collect(node.page):
                rendered = node.page.render()
                rendered.write(node.name, dir_fd=render_dir.dir_fd)
                self.build_log[os.path.join(render_dir.relpath, node.name)] = node.page

        if node.sub:
            for name, sub in node.sub.items():
                if sub.page is None or sub.sub is not None:
                    # Subdir
                    render_dir.prepare_subdir(name)
                    with render_dir.subdir(name) as subdir:
                        self.write_subtree(sub, subdir, stats)
                else:
                    # Page
                    render_dir.prepare_file(name)
                    with stats.collect(sub.page):
                        rendered = sub.page.render()
                        rendered.write(name, dir_fd=render_dir.dir_fd)
                        self.build_log[os.path.join(render_dir.relpath, name)] = sub.page

        render_dir.cleanup_leftovers()

    def output_abspath(self, relpath):
        abspath = os.path.join(self.build_root, relpath)
        os.makedirs(os.path.dirname(abspath), exist_ok=True)
        return abspath

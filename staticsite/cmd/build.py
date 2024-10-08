from __future__ import annotations

import argparse
import contextlib
import locale
import logging
import os
import shutil
import time
from collections import Counter
from collections.abc import Generator
from typing import TYPE_CHECKING, Any

from .. import render, utils
from ..page import ChangeExtent
from ..site import Path
from .command import Fail, SiteCommand, register

if TYPE_CHECKING:
    from ..node import Node
    from ..page import Page
    from ..site import Site

log = logging.getLogger("build")


@register
class Build(SiteCommand):
    "build the site into the web/ directory of the project"

    @classmethod
    def add_subparser(
        cls, subparsers: argparse._SubParsersAction[Any]
    ) -> argparse.ArgumentParser:
        parser = super().add_subparser(subparsers)
        parser.add_argument(
            "--type", action="store", help="render only pages of this type"
        )
        parser.add_argument(
            "--path", action="store", help="render only pages under this path"
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="fail the first time a page gives an error in rendering",
        )
        parser.add_argument(
            "-f", "--full", action="store_true", help="always do a full rebuild"
        )
        return parser

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.site: Site

    def run(self) -> int | None:
        self.site = self.load_site()
        self.builder = Builder(
            self.site,
            type_filter=self.args.type,
            path_filter=self.args.path,
            fail_fast=self.args.fail_fast,
            full=self.args.full,
        )
        self.builder.write()
        if self.builder.has_errors:
            return 1
        return None


class RenderStats:
    """
    Statistics collected during rendering
    """

    def __init__(self) -> None:
        self.sums: dict[str, int] = Counter()
        self.counts: dict[str, int] = Counter()

    @contextlib.contextmanager
    def collect(self, page: Page) -> Generator[None, None, None]:
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
        self.old_dirs: dict[str, os.stat_result] = {}
        self.old_files: dict[str, os.stat_result] = {}
        with os.scandir(dir_fd) as entries:
            for de in entries:
                if de.is_dir():
                    self.old_dirs[de.name] = de.stat()
                else:
                    self.old_files[de.name] = de.stat()

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

    def prepare_subdir(self, name: str) -> os.stat_result | None:
        """
        Prepare for rendering a subdirectory.

        Return a File object corresponding to an existing directory entry
        """
        if name in self.old_dirs:
            # Directory already existed: reuse it
            return self.old_dirs.pop(name)
        elif name in self.old_files:
            # There was a file at this location: delete it
            self.old_files.pop(name, None)
            os.unlink(name, dir_fd=self.dir_fd)
            os.mkdir(name, dir_fd=self.dir_fd)
            return None
        else:
            # There was nothing: create the directory
            os.mkdir(name, dir_fd=self.dir_fd)
            return None

    def prepare_file(self, name: str) -> os.stat_result | None:
        """
        Prepare for rendering a file

        Return a File object corresponding to an existing directory entry
        """
        if name in self.old_dirs:
            # There is a directory instead: remove it
            self.old_dirs.pop(name, None)
            # FIXME: from Python 3.11, rmtree supports dir_fd
            shutil.rmtree(os.path.join(self.root, self.relpath, name))
            return None
        elif name in self.old_files:
            # There is a file at this location: it will be overwritten
            return self.old_files.pop(name)
        else:
            return None

    def cleanup_leftovers(self) -> None:
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
    def __init__(
        self,
        site: Site,
        type_filter: str | None = None,
        path_filter: str | None = None,
        fail_fast: bool = False,
        full: bool = True,
    ):
        self.site = site
        self.type_filter = type_filter
        self.path_filter = path_filter
        if site.settings.PROJECT_ROOT is None:
            raise Fail("PROJECT_ROOT is not set")
        if site.settings.OUTPUT is None:
            raise Fail(
                "No output directory configured:"
                " please use --output or set OUTPUT in settings.py or .staticsite.py"
            )
        self.build_root = os.path.join(site.settings.PROJECT_ROOT, site.settings.OUTPUT)
        # Logs which pages have been rendered and to which path
        self.build_log: dict[str, Page] = {}
        self.fail_fast = fail_fast
        self.full = full
        self.has_errors = False
        self.built_marker = render.RenderedString(
            """---
skip: yes
"""
        )

    def write(self) -> None:
        """
        Generate output
        """
        # Set locale for rendering
        try:
            lname = self.site.settings.LANGUAGES[0]["locale"]
            locale.setlocale(locale.LC_ALL, lname)
        except locale.Error as e:
            log.warning("Cannot set locale to %s: %s", lname, e)

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

        with utils.timings("Saved build state in %fs"):
            if self.has_errors:
                # Output directory is partially build, a further build cannot rely on it
                self.site.clear_footprints()
            else:
                self.site.save_footprints()

        #     self.build_cache.put("git_hash", self.new_hexsha)
        #     self.build_cache.put("git_dirty", sorted(self.files_changed_in_workdir))
        #     # build_cache.put("git_dirty", repo.head.commit.hexsha)

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

    def write_single_process(self) -> None:
        root: Node = self.site.root
        if self.path_filter is not None:
            if (node := root.lookup_node(Path.from_string(self.path_filter))) is None:
                raise Fail(
                    f"path filter {self.path_filter} does not match a path in the site"
                )
            root = node
        stats = RenderStats()
        os.makedirs(self.build_root, exist_ok=True)

        with RenderDirectory.open(self.build_root) as render_dir:
            # Write built marker
            old_file = render_dir.prepare_file(".staticsite")
            self.built_marker.write(
                name=".staticsite", dir_fd=render_dir.dir_fd, old=old_file
            )

            # Write rendered contents
            self.write_subtree(root, render_dir, stats=stats)
        for type in sorted(stats.sums.keys()):
            log.info(
                "%s: %d in %.3fs (%.1f per minute)",
                type,
                stats.counts[type],
                stats.sums[type] / 1_000_000_000,
                stats.counts[type] / stats.sums[type] * 60 * 1_000_000_000,
            )

    def write_subtree(
        self, node: Node, render_dir: RenderDirectory, stats: RenderStats
    ) -> None:
        """
        Recursively render the given node in the given render directory
        """
        log.debug("write_subtree relpath:%s node:%r", render_dir.relpath, node)
        # If this is the build node for a page, render it
        for name, page in node.build_pages.items():
            if self.type_filter and page.TYPE != self.type_filter:
                continue
            if (old_file := render_dir.prepare_file(name)) is not None:
                # TODO: simple minded so far
                if not self.full and page.change_extent == ChangeExtent.UNCHANGED:
                    continue
            with stats.collect(page):
                try:
                    rendered = page.render()
                except Exception:
                    if self.fail_fast:
                        raise
                    log.error(
                        "%s:%s page failed to render",
                        render_dir.relpath,
                        name,
                        exc_info=True,
                    )
                    self.has_errors = True
                else:
                    # log.debug("write_subtree relpath:%s render %s %s", render_dir.relpath, page.TYPE, name)
                    rendered.write(name=name, dir_fd=render_dir.dir_fd, old=old_file)
                self.build_log[os.path.join(render_dir.relpath, name)] = page

        for name, sub in node.sub.items():
            # Subdir
            # log.debug("write_subtree relpath:%s render subdir %s", render_dir.relpath, name)
            render_dir.prepare_subdir(name)
            with render_dir.subdir(name) as subdir:
                self.write_subtree(sub, subdir, stats)

        render_dir.cleanup_leftovers()

    def output_abspath(self, relpath: str) -> str:
        abspath = os.path.join(self.build_root, relpath)
        os.makedirs(os.path.dirname(abspath), exist_ok=True)
        return abspath

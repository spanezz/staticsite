from __future__ import annotations

import contextlib
# import io
import locale
import logging
import os
import shutil
import time
from collections import Counter
from typing import TYPE_CHECKING, Generator, Optional

# import git

from .. import utils
from ..file import File
from ..node import Path
from .command import Fail, SiteCommand

if TYPE_CHECKING:
    # from ..cache import Cache
    from ..node import Node
    from ..page import Page
    from ..site import Site

log = logging.getLogger("build")


class Build(SiteCommand):
    "build the site into the web/ directory of the project"

    @classmethod
    def make_subparser(cls, subparsers):
        parser = super().make_subparser(subparsers)
        parser.add_argument("--type", action="store",
                            help="render only pages of this type")
        parser.add_argument("--path", action="store",
                            help="render only pages under this path")
        parser.add_argument("--fail-fast", action="store_true",
                            help="fail the first time a page gives an error in rendering")
        parser.add_argument("-f", "--full", action="store_true",
                            help="always do a full rebuild")
        return parser

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site: Site

    def run(self):
        self.site = self.load_site()
        self.builder = Builder(
                self.site, type_filter=self.args.type,
                path_filter=self.args.path, fail_fast=self.args.fail_fast,
                full=self.args.full)
        self.builder.write()
        if self.builder.has_errors:
            return 1


class RenderStats:
    """
    Statistics collected during rendering
    """
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

    def prepare_subdir(self, name: str) -> Optional[File]:
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

    def prepare_file(self, name: str) -> Optional[File]:
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
    def __init__(
            self,
            site: Site,
            type_filter: Optional[str] = None,
            path_filter: Optional[str] = None,
            fail_fast: bool = False,
            full: bool = True):
        self.site = site
        self.type_filter = type_filter
        self.path_filter = path_filter
        if self.site.settings.OUTPUT is None:
            raise Fail(
                    "No output directory configured:"
                    " please use --output or set OUTPUT in settings.py or .staticsite.py")
        self.build_root = os.path.join(site.settings.PROJECT_ROOT, site.settings.OUTPUT)
        # Logs which pages have been rendered and to which path
        self.build_log: dict[str, Page] = {}
        self.fail_fast = fail_fast
        self.full = full
        self.has_errors = False

        # # Git repository holding the source contents
        # self.repo: Optional[git.Repo] = None

        # # Cache with last build information
        # self.build_cache: Optional[Cache] = None

        # # Relative path of contents from the root of the git working dir
        # self.content_relpath: Optional[str] = None

        # # Git shasum of the last build
        # self.old_hexsha: Optional[str] = None
        # # Git shasum of this build
        # self.new_hexsha: Optional[str] = None
        # # Files that were added since last build
        # self.files_added: set[str] = set()
        # # Files that were removed since last build
        # self.files_removed: set[str] = set()
        # # Files that were changed since last build
        # self.files_changed: set[str] = set()

    # def scan_changes(self) -> bool:
    #     """
    #     List files that have changed since the last render.

    #     Returns False if we can't say anything and the whole site needs to be
    #     rebuilt. Returns True if all change structures have been filled
    #     """
    #     # Find git repository
    #     try:
    #         self.repo = git.Repo(self.site.content_root, search_parent_directories=True)
    #         log.info("Contents is stored in git at %s", self.repo.working_tree_dir)
    #     except git.exc.NoSuchPathError:
    #         log.info("Contents is not stored in git")
    #         self.repo = None
    #         return False

    #     # Find information about the last render run
    #     self.build_cache = self.site.caches.get("build")

    #     self.old_hexsha = self.build_cache.get("git_hexsha")
    #     self.old_hexsha = "86fd0905c7ca7251f73bddd67248443545ebaab5"
    #     if self.old_hexsha is None:
    #         return False

    #     self.new_hexsha = self.repo.head.commit.hexsha

    #     # Relative path of contents from the root of the git working dir
    #     self.content_relpath = os.path.relpath(self.site.content_root, self.repo.working_tree_dir)

    #     old_tree = self.repo.commit(self.old_hexsha).tree

    #     # Build an index with the sources to be rendered
    #     log.info("Timing0")
    #     new_index = git.IndexFile.from_tree(self.repo, "HEAD")
    #     log.info("Timing1")
    #     # FIXME: this takes 5 seconds to run, while it's almost instant with git!
    #     # FIXME: possibly use git-commit-tree, after git write-tree makes it from the index
    #     new_index.add(self.site.content_root)
    #     log.info("Timing2")
    #     new_index_commit = print(new_index.commit("build TODO: date", head=False, skip_hooks=True))
    #     log.info("Timing3")

    #     # See what changed
    #     for file in old_tree.diff(new_index_commit):
    #         # TODO: filter out things outside of content dir, like archetypes
    #         if file.a_blob is not None and file.b_blob is None:
    #             self.files_removed.add(os.path.relpath(file.a_path, self.content_relpath))
    #         elif file.a_blob is None and file.b_blob is not None:
    #             self.files_added.add(os.path.relpath(file.b_path, self.content_relpath))
    #         else:
    #             self.files_changed.add(os.path.relpath(file.a_path, self.content_relpath))

    #     # TODO: at the end, reference the commit with a staticsite tag or branch
    #     # TODO: if rendering failed, remove the commit

    #     # after rendering make a commit in git with the last stuff we rendered.
    #     # Next render, diff from that

    #     # # Dirty, unstaged
    #     # for file in self.repo.index.diff(None):
    #     #     if file.a_blob is not None and file.b_blob is None:
    #     #         print("REMOVED1", file.a_path)
    #     #     elif file.a_blob is None and file.b_blob is not None:
    #     #         print("ADDED1", file.a_path)
    #     #     self.files_changed_in_workdir.add(os.path.relpath(file.a_path, self.content_relpath))
    #     # # Dirty, staged
    #     # for file in self.repo.index.diff("HEAD"):
    #     #     if file.a_blob is not None and file.b_blob is None:
    #     #         print("REMOVED2", file.a_path)
    #     #     elif file.a_blob is None and file.b_blob is not None:
    #     #         print("ADDED2", file.a_path)
    #     #     self.files_changed_in_workdir.add(os.path.relpath(file.a_path, self.content_relpath))

    #     return True

    # def get_incremental_page_set(self) -> Optional[set[Page]]:
    #     """
    #     Return the set of pages that can be built incrementally, or None if we
    #     need a full rebuild
    #     """
    #     if self.full:
    #         return None

    #     log.info("Scanning for changes using git")
    #     self.scan_changes()
    #     if self.files_added or self.files_removed:
    #         # For now, always rebuild all
    #         for relpath in self.files_added:
    #             log.info("%s: file added", relpath)
    #         for relpath in self.files_removed:
    #             log.info("%s: file removed", relpath)
    #         log.info("Files were added or removed: triggering full rebuild")
    #         return None

    #     if not self.files_changed:
    #         log.info("All sources are unchanged")
    #         # Empty set, to mean incremental build with no pages changed
    #         return set()
    #     elif len(self.files_changed) > 20:
    #         log.info("Too many (%d) sources changed, triggering full rebuild", len(self.files_changed))
    #         # Rebuild all after some threshold
    #         return None
    #     else:
    #         # TODO: if it's only rst or markdown, and meta haven't changed,
    #         # rebuild only those?
    #         tree = self.repo.commit(self.old_hexsha).tree
    #         incremental_pages: set[Page] = set()
    #         for relpath in self.files_changed:
    #             log.info("%s: file changed", relpath)
    #             page = self.site.find_page(relpath)
    #             old_blob = tree[os.path.join(self.content_relpath, relpath)]
    #             if (fmc := getattr(page, "front_matter_changed", None)) is None:
    #                 # TODO: always changed, since we can't compare front matter
    #                 log.info("%s: change in complex file, triggering full rebuild", page)
    #                 return None
    #             else:
    #                 # In theory we could read from old_blob.data_stream.stream.
    #                 # In practice iterating it line by line hits a
    #                 # recursion limit, and it may be a gitpython bug:
    #                 # git/cmd.py: CatFileContentStream.__next__ calls next(self)
    #                 # TODO: investigate/reporte
    #                 # However, data_stream.stream will always read the
    #                 # whole page anyway, so we lose nothing in using a
    #                 # BytesIO
    #                 with io.BytesIO() as fd:
    #                     old_blob.stream_data(fd)
    #                     fd.seek(0)
    #                     if fmc(fd):
    #                         log.info("%s: front matter changed, triggering full rebuild", page)
    #                         return None
    #                     else:
    #                         log.info("%s: front matter unchanged, can rebuild incrementally", page)
    #                         incremental_pages.add(page)

    #         return incremental_pages

    def write(self):
        """
        Generate output
        """
        # self.incremental_pages = self.get_incremental_page_set()
        # if self.incremental_pages is not None:
        #     log.info("Running incremental build with %d changed pages", len(self.incremental_pages))

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

        # if not self.has_errors:
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

    def write_single_process(self):
        root = self.site.root
        if self.path_filter is not None:
            root = root.lookup(Path.from_string(self.path_filter))
        stats = RenderStats()
        os.makedirs(self.build_root, exist_ok=True)
        with RenderDirectory.open(self.build_root) as render_dir:
            self.write_subtree(root, render_dir, stats=stats)
        for type in sorted(stats.sums.keys()):
            log.info("%s: %d in %.3fs (%.1f per minute)",
                     type,
                     stats.counts[type],
                     stats.sums[type] / 1_000_000_000,
                     stats.counts[type] / stats.sums[type] * 60 * 1_000_000_000)

    def write_subtree(self, node: Node, render_dir: RenderDirectory, stats: RenderStats):
        """
        Recursively render the given node in the given render directory
        """
        log.debug("write_subtree relpath:%s node:%r", render_dir.relpath, node)
        # If this is the build node for a page, render it
        for name, page in node.build_pages.items():
            if self.type_filter and page.TYPE != self.type_filter:
                continue
            if (old_file := render_dir.prepare_file(name)) is not None:
                pass
                # if self.incremental_pages is not None and page not in self.incremental_pages:
                #     continue
            with stats.collect(page):
                try:
                    rendered = page.render()
                except Exception:
                    if self.fail_fast:
                        raise
                    log.error("%s:%s page failed to render", render_dir.relpath, name, exc_info=True)
                    self.has_errors = True
                else:
                    # log.debug("write_subtree relpath:%s render %s %s", render_dir.relpath, page.TYPE, name)
                    rendered.write(name=name, dir_fd=render_dir.dir_fd, old=old_file)
                self.build_log[os.path.join(render_dir.relpath, name)] = page

        if node.sub:
            for name, sub in node.sub.items():
                # Subdir
                # log.debug("write_subtree relpath:%s render subdir %s", render_dir.relpath, name)
                render_dir.prepare_subdir(name)
                with render_dir.subdir(name) as subdir:
                    self.write_subtree(sub, subdir, stats)

        render_dir.cleanup_leftovers()

    def output_abspath(self, relpath):
        abspath = os.path.join(self.build_root, relpath)
        os.makedirs(os.path.dirname(abspath), exist_ok=True)
        return abspath

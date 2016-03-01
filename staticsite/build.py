# coding: utf-8

import json
import os
import re
import time
import shutil
from .commands import SiteCommand, CmdlineError
import logging

log = logging.getLogger()

class Build(SiteCommand):
    "build the site into the web/ directory of the project"

    def run(self):
        site = self.load_site()
        start = time.perf_counter()
        self.write(site)
        end = time.perf_counter()
        log.info("Built site in %fs", end-start)

    def clear_outdir(self, outdir):
        for f in os.listdir(outdir):
            abs = os.path.join(outdir, f)
            if os.path.isdir(abs):
                shutil.rmtree(abs)
            else:
                os.unlink(abs)

    def write(self, site):
        """
        Generate output
        """
        # Clear the target directory, but keep the root path so that a web
        # server running on it does not find itself running nowhere
        outdir = os.path.join(self.root, "web")
        if os.path.exists(outdir):
            self.clear_outdir(outdir)

        # cpu_count = os.cpu_count()
        # if cpu_count > 1:
        #     self.write_multi_process(site, cpu_count)
        # else:
        #     self.write_single_process(site)

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
        self.write_single_process(site)

    def write_multi_process(self, site, child_count):
        log.info("Generating pages using %d child processes", child_count)

        pages = list(site.pages.values())

        # From http://code.activestate.com/recipes/576785-partition-an-iterable-into-n-lists/
        chunks = [pages[i::child_count] for i in range(child_count)]

        print(len(pages))
        for c in chunks:
            print(len(c))

        import sys
        pids = set()
        for chunk in chunks:
            pid = os.fork()
            if pid == 0:
                self.write_pages(chunk)
                sys.exit(0)
            else:
                pids.add(pid)

        while pids:
            (pid, status) = os.wait()
            pids.discard(pid)

    def write_single_process(self, site):
        self.write_pages(site.pages.values())

    def write_pages(self, pages):
        for page in pages:
            for relpath, rendered in page.render().items():
                dst = self.output_abspath(relpath)
                rendered.write(dst)

    def output_abspath(self, relpath):
        abspath = os.path.join(self.root, "web", relpath)
        os.makedirs(os.path.dirname(abspath), exist_ok=True)
        return abspath

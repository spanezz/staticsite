# coding: utf-8

import json
import os
import re
import time
import shutil
from collections import defaultdict
from .commands import SiteCommand, CmdlineError
from .utils import timings
import logging

log = logging.getLogger()

class Build(SiteCommand):
    "build the site into the web/ directory of the project"

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def run(self):
        site = self.load_site()
        builder = Builder(self.root, site)
        builder.write()


class Builder:
    def __init__(self, root, site):
        self.site = site
        self.output_root = os.path.join(root, site.settings.OUTPUT)

    def clear_outdir(self, outdir):
        for f in os.listdir(outdir):
            abs = os.path.join(outdir, f)
            if os.path.isdir(abs):
                shutil.rmtree(abs)
            else:
                os.unlink(abs)

    def write(self):
        """
        Generate output
        """
        # Clear the target directory, but keep the root path so that a web
        # server running on it does not find itself running nowhere
        if os.path.exists(self.output_root):
            with timings("Cleaned output directory in %fs"):
                self.clear_outdir(self.output_root)

        with timings("Built site in %fs"):
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

    def write_multi_process(self, child_count):
        log.info("Generating pages using %d child processes", child_count)

        pages = list(self.site.pages.values())

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

    def write_single_process(self):
        sums, counts = self.write_pages(self.site.pages.values())
        for type in sorted(sums.keys()):
            log.info("%s: %d in %.3fs (%.1f per minute)", type, counts[type], sums[type], counts[type]/sums[type] * 60)

    def write_pages(self, pages):
        sums = defaultdict(float)
        counts = defaultdict(int)

        # group by type
        by_type = defaultdict(list)
        for page in pages:
            by_type[(page.RENDER_PREFERRED_ORDER, page.TYPE)].append(page)

        # Render collecting timing statistics
        for (order, type), pgs in sorted(by_type.items(), key=lambda x:x[0][0]):
            start = time.perf_counter()
            for page in pgs:
                contents = page.render()
                for relpath, rendered in contents.items():
                    dst = self.output_abspath(relpath)
                    rendered.write(dst)
            end = time.perf_counter()
            sums[type] = end - start
            counts[type] = len(pgs)
        return sums, counts

    def output_abspath(self, relpath):
        abspath = os.path.join(self.output_root, relpath)
        os.makedirs(os.path.dirname(abspath), exist_ok=True)
        return abspath

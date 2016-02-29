# coding: utf-8

import json
import os
import re
import shutil
import logging

log = logging.getLogger()


class WebWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

    def clear_outdir(self, outdir):
        for f in os.listdir(outdir):
            abs = os.path.join(outdir, f)
            if os.path.isdir(abs):
                shutil.rmtree(abs)
            else:
                os.unlink(abs)

    def write(self, site):
        # Clear the target directory, but keep the root path so that a web
        # server running on it does not find itself running nowhere
        outdir = os.path.join(self.root, "web")
        if os.path.exists(outdir):
            self.clear_outdir(outdir)

        # Generate output
        for page in site.pages.values():
            for relpath, rendered in page.render().items():
                dst = self.output_abspath(relpath)
                rendered.write(dst)

    def output_abspath(self, relpath):
        abspath = os.path.join(self.root, "web", relpath)
        os.makedirs(os.path.dirname(abspath), exist_ok=True)
        return abspath


from __future__ import annotations
from typing import Tuple, Dict, Any
import os
import logging

log = logging.getLogger("archetypes")


class Archetype:
    def __init__(self, archetypes, relpath):
        self.archetypes = archetypes
        self.site = archetypes.site
        self.relpath = relpath

    def render(self, **kw) -> Tuple[Dict[str, Any], str]:
        """
        Render the archetype with the given context information.

        Returns the metadata of the rendered page, and the rendered page
        contents.
        """
        # By default, render the archetype with jinja2
        abspath = os.path.join(self.archetypes.root, self.relpath)
        with open(abspath, "rt") as fd:
            template = self.site.theme.jinja2.from_string(fd.read())
        rendered = template.render(**kw)
        return {}, rendered


class Archetypes:
    def __init__(self, site, root):
        self.site = site

        # Root directory where archetypes are found
        self.root = root

    def find(self, name: str):
        """
        Read the archetypes directory and return the archetype that matches the given name.

        Returns None if nothing matches.
        """
        for root, dnames, fnames in os.walk(self.root, followlinks=True):
            for f in fnames:
                if f.startswith("."):
                    continue
                relpath = os.path.relpath(os.path.join(root, f), self.root)
                for feature in self.site.features.ordered():
                    a = feature.try_load_archetype(self, relpath, name)
                    if a is not None:
                        return a
        return None

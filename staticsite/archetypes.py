# coding: utf-8
import os
import logging

log = logging.getLogger()


class Archetypes:
    def __init__(self, site, root):
        self.site = site

        # Root directory where archetypes are found
        self.root = root

    def find(self, name):
        """
        Read the archetypes directory and return the archetype that matches the given name.

        Returns None if nothing matches.
        """
        for root, dnames, fnames in os.walk(self.root):
            for f in fnames:
                if f.startswith("."):
                    continue
                relpath = os.path.relpath(os.path.join(root, f), self.root)
                for name, feature in self.site.features.items():
                    a = feature.try_load_archetype(self, relpath, name)
                    if a is not None:
                        return a
        return None

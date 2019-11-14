from __future__ import annotations
from typing import Optional, Dict, Callable
from collections import defaultdict
from .page import Page
from . import site


class Feature:
    def __init__(self, site: "site.Site"):
        self.site = site
        # Feature-provided jinja2 globals
        self.j2_globals: Dict[str, Callable] = {}
        # Feature-provided jinja2 filters
        self.j2_filters: Dict[str, Callable] = {}
        # Names of page.meta elements that are relevant to this feature
        self.for_metadata = []

    def add_page(self, page):
        """
        Add a page to this series, when it contains one of the metadata items
        defined in for_metadata
        """
        raise NotImplementedError("Feature.add_page")

    def try_load_page(self, root_abspath: str, relpath: str) -> Optional[Page]:
        """
        Try loading a page from the given path.

        Returns None if this path is not handled by this Feature
        """
        return None

    def try_load_archetype(self, archetypes, relpath, name):
        """
        Try loading an archetype page.

        Returns None if this path is not handled by this feature
        """
        return None

    def build_test_page(self, **kw) -> Page:
        """
        Build a test page
        """
        raise NotImplementedError

    def finalize(self):
        """
        Hook called after all the pages have been loaded
        """
        pass


class Features:
    def __init__(self, site: site.Site):
        self.site = site

        # Feature implementation registry
        self.features: Dict[str, Feature] = {}

        # Metadata names that trigger feature hooks when loading pages
        self.metadata_hooks: Dict[str, Feature] = defaultdict(list)

    def add(self, name, cls):
        """
        Add a feature class to the site
        """
        feature = cls(self.site)
        self.features[name] = feature
        # Index features for metadata hooks
        for name in feature.for_metadata:
            self.metadata_hooks[name].append(feature)

    def ordered(self):
        return self.features.values()

    def __getitem__(self, key):
        return self.features[key]

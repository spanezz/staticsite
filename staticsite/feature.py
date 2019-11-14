from __future__ import annotations
from typing import Optional, Dict, Callable, Set, List
from collections import defaultdict
import logging
from .page import Page
from . import site
from . import toposort

log = logging.getLogger()


class Feature:
    # List names of features that should run after us.
    # The dependency order is taken into account when calling try_load_page and
    # finalize.
    RUN_BEFORE: List[str] = []

    # List names of features that should run before us.
    # The dependency order is taken into account when calling try_load_page and
    # finalize.
    RUN_AFTER: List[str] = []

    def __init__(self, name: str, site: "site.Site"):
        # Feature name
        self.name = name
        # Site object
        self.site = site
        # Feature-provided jinja2 globals
        self.j2_globals: Dict[str, Callable] = {}
        # Feature-provided jinja2 filters
        self.j2_filters: Dict[str, Callable] = {}
        # Names of page.meta elements that are relevant to this feature
        self.for_metadata = []

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.name)

    def get_short_description(self):
        """
        Get a short description from this feature's docstring
        """
        if not self.__doc__:
            return ""
        else:
            return self.__doc__.lstrip().splitlines()[0].strip()

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

        # Features sorted by topological order
        self.sorted = None

    def add(self, name, cls):
        """
        Add a feature class to the site
        """
        feature = cls(name, self.site)
        self.features[name] = feature
        # Index features for metadata hooks
        for name in feature.for_metadata:
            self.metadata_hooks[name].append(feature)

    def ordered(self):
        return self.sorted

    def __getitem__(self, key):
        return self.features[key]

    def commit(self):
        graph: Dict[Feature, Set[Feature]] = defaultdict(set)
        for feature in self.features.values():
            for name in feature.RUN_AFTER:
                dep = self.features.get(name)
                if dep is None:
                    log.warn("feature %s: ignoring RUN_AFTER relation on %s which is not available",
                             feature.name, name)
                    continue
                graph[dep].add(feature)

            for name in feature.RUN_BEFORE:
                dep = self.features.get(name)
                if dep is None:
                    log.warn("feature %s: ignoring RUN_BEFORE relation on %s which is not available",
                             feature.name, name)
                    continue
                graph[feature].add(dep)

        self.sorted = toposort.sort(graph)
        log.debug("sorted feature list: %r", [x.name for x in self.sorted])

from __future__ import annotations
from typing import Optional, Dict, Callable, Set, List, Iterable
from collections import defaultdict
import logging
import sys
from .page import Page
from .render import File
from . import site
from . import toposort

log = logging.getLogger()


class Feature:
    """
    Base class for implementing a staticsite feature.

    It contains dependencies on other features, and hooks called in various
    stages of site processing.
    """
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

    def try_load_page(self, file: File) -> Optional[Page]:
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

    def add_site_commands(self, subparsers):
        """
        Add commands to `ssite site --cmd …` command line parser
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

    def _sort_features(self, features: Iterable[Feature], all_features: Dict[str, Feature]):
        graph: Dict[Feature, Set[Feature]] = defaultdict(set)
        for feature in features:
            for name in feature.RUN_AFTER:
                dep = all_features.get(name)
                if dep is None:
                    log.warn("feature %s: ignoring RUN_AFTER relation on %s which is not available",
                             feature, name)
                    continue
                graph[dep].add(feature)

            for name in feature.RUN_BEFORE:
                dep = all_features.get(name)
                if dep is None:
                    log.warn("feature %s: ignoring RUN_BEFORE relation on %s which is not available",
                             feature, name)
                    continue
                graph[feature].add(dep)

        return toposort.sort(graph)

    def commit(self):
        self.sorted = self._sort_features(self.features.values(), self.features)
        log.debug("sorted feature list: %r", [x.name for x in self.sorted])

    def load_default_features(self):
        """
        Load features packaged with staticsite
        """
        from . import features
        self.load_feature_dir(features.__path__)

    def load_feature_dir(self, paths, namespace="staticsite.features"):
        """
        Load all features found in the given directory.

        Feature classes are instantiate in dependency order.
        """
        import pkgutil
        import importlib

        feature_classes = {}
        for module_finder, name, ispkg in pkgutil.iter_modules(paths):
            full_name = namespace + "." + name
            mod = sys.modules.get(full_name)
            if not mod:
                try:
                    spec = module_finder.find_spec(name)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                except Exception:
                    log.exception("%r: failed to load feature module", name)
                    continue
                sys.modules[full_name] = mod

            features = getattr(mod, "FEATURES", None)
            if features is None:
                log.warn("%r: feature module did not define a FEATURES dict", name)
                continue

            # Register features with site
            for name, cls in features.items():
                cls.NAME = name
                feature_classes[name] = cls

        # Instantiate the feature classes in dependency order
        for cls in self._sort_features(feature_classes.values(), feature_classes):
            self.add(cls.NAME, cls)

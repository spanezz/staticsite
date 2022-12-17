from __future__ import annotations

import logging
import sys
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Type

from . import file, fstree, site, toposort, fields
from .node import Node
from .page import Page

log = logging.getLogger("feature")


class TrackedFieldMixin:
    """
    Leat a feature track when values are set on this field
    """
    tracked_by: str

    def __init__(self, *, tracked_by: Optional[str] = None, **kw):
        """
        :arg tracked_by: name of a feature that is notified when field values
                         are ses
        """
        super().__init__(**kw)
        if tracked_by is not None:
            self.tracked_by = tracked_by
        self.track_feature_key: str

    def __set_name__(self, owner: Type[fields.FieldContainer], name: str) -> None:
        super().__set_name__(owner, name)
        self.track_feature_key = f"_{self.name}_feature"

    def track(self, obj: fields.FieldContainer, value: Any):
        # We cannot store a reference to the Feature in the field, because it
        # would persist in the class definition, making it impossible to build
        # two sites one after the other.
        if (feature := obj.__dict__.get(self.track_feature_key)) is None:
            feature = obj.site.features[self.tracked_by]
            obj.__dict__[self.track_feature_key] = feature
        feature.track_field(self, obj, value)

    def __set__(self, obj: fields.FieldContainer, value: Any) -> None:
        self.track(obj, value)
        super().__set__(obj, value)


class Feature:
    """
    Base class for implementing a staticsite feature.

    It contains dependencies on other features, and hooks called in various
    stages of site processing.
    """
    # Name with which the feature class was loaded
    NAME: str

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
        # Feature-provided node mixins
        self.node_mixins = []
        # Feature-provided page mixins
        self.page_mixins = []

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

    def load_dir_meta(self, directory: fstree.Tree) -> Optional[dict[str, Any]]:
        """
        Hook to load extra directory metadata for the given sitedir.

        sitedir will be already populated with directory contents, but not yet
        loaded.
        """
        # Do nothing by default
        return None

    def load_dir(
            self,
            node: Node,
            directory: fstree.Tree,
            files: dict[str, tuple[dict[str, Any], file.File]]) -> list[Page]:
        """
        Load pages from the given Dir.

        Remove from dir the filenames that have been loaded.

        Return the list of loaded pages.
        """
        return []

    def try_load_archetype(self, archetypes, relpath, name):
        """
        Try loading an archetype page.

        Returns None if this path is not handled by this feature
        """
        return None

    def organize(self):
        """
        Hook called after all the pages have been loaded
        """
        pass

    def generate(self):
        """
        Hook called after loaded pages have been organized, to autogenerate new
        pages
        """
        pass

    def crossreference(self):
        """
        Hook called after autogenerated pages have been added and the site
        structure is stable
        """
        pass

    def add_site_commands(self, subparsers):
        """
        Add commands to `ssite site --cmd …` command line parser
        """
        pass

    def get_used_page_types(self) -> list[Type[Page]]:
        """
        Return a list of the page types used by this feature
        """
        return []

    def get_footprint(self) -> dict[str, Any]:
        """
        Return information that will be cached until the next build to allow
        incremental updates
        """
        return {}

    def set_previous_footprint(self, footprint: dict[str, Any]):
        """
        Notify the feature of a cached footprint from a previous build
        """
        pass

    def track_field(self, field: fields.Field, obj: fields.FieldContainer, value: Any):
        """
        Notify the feature that the value for a field of interest is being set
        on a page
        """
        pass


class Features:
    def __init__(self, site: site.Site):
        self.site = site

        # Registry of feature classes by name, built during loading
        self.feature_classes: dict[str, Type[Feature]] = {}

        # Feature implementation registry
        self.features: dict[str, Feature] = {}

        # Mixins provided by features to add to Node classes
        self.node_mixins: list[Type] = []

        # Mixins provided by features to add to Page classes
        self.page_mixins: list[Type] = []

        # Cached final node class
        self.node_class: Optional[Type[Node]] = None

        # Cached final page classes indexed by original page class
        self.page_classes: dict[Type[Page], Type[Page]] = {}

        # Features sorted by topological order
        self.sorted = None

    def get_node_class(self) -> Type[Node]:
        """
        Return the Node class to use for this site
        """
        if self.node_class is None:
            self.node_class = type("Node", tuple(self.node_mixins) + (Node,), {})
        return self.node_class

    def get_page_class(self, cls: Type[Page]) -> Type[Page]:
        """
        Given a base Page class, return its version with added mixins
        """
        if (final := self.page_classes.get(cls)):
            return final
        # TODO: skip adding mixins to Asset pages?
        final = type(cls.__name__, tuple(self.page_mixins) + (cls,), {
            "__doc__": cls.__doc__, "__module__": cls.__module__
        })
        self.page_classes[cls] = final
        return final

    def ordered(self):
        return self.sorted

    def __getitem__(self, key):
        return self.features[key]

    def get(self, key, default=None):
        return self.features.get(key, default)

    def _sort_features(self, features: Dict[str, Feature]):
        graph: Dict[str, Set[str]] = defaultdict(set)

        # Add well-known synchronization points
        graph["autogenerated_pages"]

        # Add feature dependencies
        for feature in features.values():
            # Make sure that each feature is in the graph
            graph[feature.NAME] = set()

            for name in feature.RUN_AFTER:
                if name not in features and name not in graph:
                    log.warn("feature %s: ignoring RUN_AFTER relation on %s which is not available",
                             feature, name)
                    continue
                graph[feature.NAME].add(name)

            for name in feature.RUN_BEFORE:
                if name not in features and name not in graph:
                    log.warn("feature %s: ignoring RUN_BEFORE relation on %s which is not available",
                             feature, name)
                    continue
                graph[name].add(feature.NAME)

        # Build the sorted list of features
        sorted_names = toposort.sort(graph)
        log.debug("Feature run order: %r", sorted_names)
        sorted_features = []
        for name in sorted_names:
            f = features.get(name)
            # Skip names that are not features, like well-known synchronization
            # points
            if f is None:
                continue
            sorted_features.append(f)
        return sorted_features

    def commit(self):
        """
        Finalize feature loading, instantiating and initializing all the
        features that have been collected.
        """
        self.sorted = []

        # Instantiate the feature classes in dependency order
        for cls in self._sort_features(self.feature_classes):
            if cls.NAME in self.features:
                continue
            feature = cls(cls.NAME, self.site)
            self.features[cls.NAME] = feature
            self.sorted.append(feature)
            self.node_mixins += feature.node_mixins

        log.debug("sorted feature list: %r", [x.name for x in self.sorted])

    def contents_scanned(self):
        """
        Hook called when the site is done scanning contents, and before
        instantiating pages
        """
        for feature in self.sorted:
            self.page_mixins += feature.page_mixins

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
        import importlib
        import pkgutil

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
                old = self.feature_classes.get(name)
                if old is not None:
                    # Allows replacing features: see #28
                    log.info("%s: replacing feature %s with %s", name, old, cls)
                self.feature_classes[name] = cls


class PageTrackingMixin:
    """
    Basic page tracking functionality for features that need it
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        # Collect pages notified by track_field, regardless of field name
        self.tracked_pages: set[Page] = set()

    def track_field(self, field: fields.Field, obj: fields.FieldContainer, value: Any):
        self.tracked_pages.add(obj)

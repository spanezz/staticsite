from __future__ import annotations
from typing import Optional, Dict
import os
import pytz
import datetime
from collections import defaultdict
from .settings import Settings
from .page import Page
import logging

log = logging.getLogger()


class Site:
    def __init__(self, settings: Optional[Settings] = None):
        from .feature import Feature

        # Site settings
        if settings is None:
            settings = Settings()
        self.settings: Settings = settings

        # Site pages
        self.pages: Dict[str, Page] = {}

        # Site time zone
        self.timezone = pytz.timezone(settings.TIMEZONE)

        # Current datetime
        self.generation_time = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(self.timezone)

        # Theme used to render pages
        self.theme = None

        # If true, do not ignore pages with dates in the future
        self.draft: bool = False

        # Feature implementation registry
        self.features: Dict[str, Feature] = {}

        # Metadata names that trigger feature hooks when loading pages
        self.feature_metadata_hooks: Dict[str, Feature] = defaultdict(list)

    def load_features(self):
        # Load default features
        from .features.markdown import MarkdownPages
        self.add_feature("md", MarkdownPages)

        from .features.j2 import J2Pages
        self.add_feature("j2", J2Pages)

        from .features.data import DataPages
        self.add_feature("data", DataPages)

        from .features.taxonomy import TaxonomyPages
        self.add_feature("taxonomies", TaxonomyPages)

        from .features.dir import DirPages
        self.add_feature("dirs", DirPages)

        from .features.series import SeriesFeature
        self.add_feature("series", SeriesFeature)

    def add_feature(self, name, cls):
        """
        Add a feature class to the site
        """
        feature = cls(self)
        self.features[name] = feature
        # Index features for metadata hooks
        for name in feature.for_metadata:
            self.feature_metadata_hooks[name].append(feature)

    def load_theme(self, theme_root):
        """
        Load a theme from the given directory.

        This needs to be called once (and only once) before analyze() is
        called.
        """
        if self.theme is not None:
            raise RuntimeError("cannot load theme from {} because it was already loaded from {}".format(
                theme_root, self.theme.root))

        from .theme import Theme
        self.theme = Theme(self, theme_root)

        theme_static = os.path.join(theme_root, "static")
        if os.path.isdir(theme_static):
            self.read_asset_tree(theme_static)

        for name in self.settings.SYSTEM_ASSETS:
            root = os.path.join("/usr/share/javascript", name)
            if not os.path.isdir(root):
                log.warning("%s: system asset directory not found", root)
                continue
            self.read_asset_tree("/usr/share/javascript", name)

    def load_content(self, content_root):
        """
        Load site page and assets from the given directory.

        Can be called multiple times.
        """
        self.read_contents_tree(content_root)

    def add_page(self, page: Page):
        """
        Add a Page object to the site.

        Use this only when the normal Site content loading functions are not
        enough. This is exported as a public function mainly for the benefit of
        unit tests.
        """
        ts = page.meta.get("date", None)
        if not self.draft and ts is not None and ts > self.generation_time:
            log.info("Ignoring page %s with date %s in the future", page.src_relpath, ts - self.generation_time)
            return
        self.pages[page.src_linkpath] = page

        # Run feature metadata hooks for the given page, if any
        trigger_features = set()
        for name, features in self.feature_metadata_hooks.items():
            if name in page.meta:
                for feature in features:
                    trigger_features.add(feature)
        for feature in trigger_features:
            feature.add_page(page)

    def add_test_page(self, feature: str, **kw) -> Page:
        """
        Add a test page instantiated using the given feature.

        :return:the Page added
        """
        page = self.features[feature].build_test_page(**kw)
        self.add_page(page)
        return page

    def read_contents_tree(self, tree_root):
        """
        Read static assets and pages from a directory and all its subdirectories
        """
        from .asset import Asset

        log.info("Loading pages from %s", tree_root)

        for root, dnames, fnames in os.walk(tree_root):
            for i, d in enumerate(dnames):
                if d.startswith("."):
                    del dnames[i]

            for f in fnames:
                if f.startswith("."):
                    continue

                page_abspath = os.path.join(root, f)
                page_relpath = os.path.relpath(page_abspath, tree_root)

                for handler in self.features.values():
                    p = handler.try_load_page(tree_root, page_relpath)
                    if p is not None:
                        self.add_page(p)
                        break
                else:
                    if os.path.isfile(page_abspath):
                        log.debug("Loading static file %s", page_relpath)
                        p = Asset(self, tree_root, page_relpath)
                        self.add_page(p)

    def read_asset_tree(self, tree_root, subdir=None):
        """
        Read static assets from a directory and all its subdirectories
        """
        from .asset import Asset

        if subdir is None:
            search_root = tree_root
        else:
            search_root = os.path.join(tree_root, subdir)

        log.info("Loading assets from %s", search_root)

        for root, dnames, fnames in os.walk(search_root):
            for f in fnames:
                if f.startswith("."):
                    continue

                page_abspath = os.path.join(root, f)
                if not os.path.isfile(page_abspath):
                    continue

                page_relpath = os.path.relpath(page_abspath, tree_root)
                log.debug("Loading static file %s", page_relpath)
                p = Asset(self, tree_root, page_relpath)
                self.add_page(p)

    def analyze(self):
        """
        Iterate through all Pages in the site to build aggregated content like
        taxonomies and directory indices.

        Call this after all Pages have been added to the site.
        """
        # Call finalize hook on features
        for feature in self.features.values():
            feature.finalize()

    def slugify(self, text):
        """
        Return the slug version of an arbitrary string, that can be used as an
        url component or file name.
        """
        from slugify import slugify
        return slugify(text)

from __future__ import annotations
from typing import Optional, Dict, List, Set, Any
import os
import pytz
import datetime
from collections import defaultdict
from .settings import Settings
from .page import Page
from .cache import Caches, DisabledCaches
from .utils import lazy, open_dir_fd
import logging

log = logging.getLogger("site")

Meta = Dict[str, Any]


class Site:
    """
    A staticsite site.

    This class tracks all resources associated with a site.
    """

    def __init__(self, settings: Optional[Settings] = None):
        from .feature import Features

        # Site settings
        if settings is None:
            settings = Settings()
        self.settings: Settings = settings

        # Fill in settings left empty that have meaningful defaults
        if self.settings.PROJECT_ROOT is None:
            self.settings.PROJECT_ROOT = os.getcwd()
        if self.settings.CONTENT is None:
            self.settings.CONTENT = "."

        # Site pages indexed by site_relpath
        self.pages: Dict[str, Page] = {}

        # Site pages indexed by src.relpath
        self.pages_by_src_relpath: Dict[str, Page] = {}

        # Site directory metadata
        self.dir_meta: Dict[str, Meta] = {}

        # Metadata for which we add pages to pages_by_metadata
        self.tracked_metadata: Set[str] = set()

        # Site pages that have the given metadata
        self.pages_by_metadata: Dict[str, List[Page]] = defaultdict(list)

        # Site time zone
        if settings.TIMEZONE is None:
            from dateutil.tz import tzlocal
            self.timezone = tzlocal()
        else:
            self.timezone = pytz.timezone(settings.TIMEZONE)

        # Current datetime
        self.generation_time = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(self.timezone)

        # Theme used to render pages
        self.theme = None

        # Feature implementation registry
        self.features = Features(self)

        # Build cache repository
        if self.settings.CACHE_REBUILDS:
            if os.access(self.settings.PROJECT_ROOT, os.W_OK):
                self.caches = Caches(os.path.join(self.settings.PROJECT_ROOT, ".staticsite-cache"))
            else:
                log.warn("%s: directory not writable: disabling caching", self.settings.PROJECT_ROOT)
                self.caches = DisabledCaches()
        else:
            self.caches = DisabledCaches()

        # Content root for the website
        self.content_root = os.path.join(self.settings.PROJECT_ROOT, self.settings.CONTENT)

    @lazy
    def archetypes(self) -> "archetypes.Archetypes":
        """
        Archetypes defined in the site
        """
        from .archetypes import Archetypes
        return Archetypes(self, os.path.join(self.settings.PROJECT_ROOT, "archetypes"))

    def find_theme_root(self) -> str:
        """
        Choose a theme root from the ones listed in the configuration
        """
        # Pick the first valid theme directory
        candidate_themes = self.settings.THEME
        if isinstance(candidate_themes, str):
            candidate_themes = (candidate_themes,)

        for theme_root in candidate_themes:
            theme_root = os.path.join(self.settings.PROJECT_ROOT, theme_root)
            if os.path.isdir(theme_root):
                return theme_root

        raise RuntimeError(
                "None of the configured theme directories ({}) seem to exist".format(
                    ", ".join(self.settings.THEME)))

    def load_theme(self):
        """
        Load a theme from the given directory.

        This needs to be called once (and only once) before analyze() is
        called.
        """
        if self.theme is not None:
            raise RuntimeError(
                    F"load_theme called while a theme was already loaded from {self.theme.root}")

        theme_root = self.find_theme_root()

        from .theme import Theme
        self.theme = Theme(self, theme_root)

    def _settings_to_meta(self) -> Meta:
        """
        Build directory metadata based on site settings
        """
        meta = {}
        if self.settings.SITE_URL:
            meta["site_url"] = self.settings.SITE_URL
        if self.settings.SITE_ROOT:
            meta["site_root"] = self.settings.SITE_ROOT
        if self.settings.SITE_NAME:
            meta["site_name"] = self.settings.SITE_NAME
        if self.settings.SITE_AUTHOR:
            meta["author"] = self.settings.SITE_AUTHOR
        return meta

    def load_content(self, content_root=None):
        """
        Load site page and assets from the given directory.

        Can be called multiple times.

        :arg content_root: path to read contents from. If missing,
                           settings.CONTENT is used.
        """
        from .contents import ContentDir
        if content_root is None:
            content_root = self.content_root

        if not os.path.exists(content_root):
            log.info("%s: content tree does not exist", content_root)
            return
        else:
            log.info("Loading pages from %s", content_root)

        with open_dir_fd(content_root) as dir_fd:
            root = ContentDir(self, content_root, "", dir_fd, meta=self._settings_to_meta())
            self.theme.load_assets()
            root.load()

    def load_asset_tree(self, tree_root, subdir=None):
        """
        Read static assets from a directory and all its subdirectories
        """
        from .contents import AssetDir

        root_meta = self.dir_meta.get("")
        if root_meta is None:
            root_meta = self._settings_to_meta()

        if subdir:
            log.info("Loading assets from %s / %s", tree_root, subdir)
            with open_dir_fd(os.path.join(tree_root, subdir)) as dir_fd:
                root = AssetDir(self, tree_root, subdir, dir_fd, dest_subdir="static", meta=root_meta)
                root.load()
        else:
            log.info("Loading assets from %s", tree_root)
            with open_dir_fd(tree_root) as dir_fd:
                root = AssetDir(self, tree_root, "", dir_fd, dest_subdir="static", meta=root_meta)
                root.load()

    def load(self, content_root=None):
        """
        Load all site components
        """
        self.features.load_default_features()
        self.load_theme()
        self.load_content(content_root=content_root)

    def add_page(self, page: Page):
        """
        Add a Page object to the site.

        Use this only when the normal Site content loading functions are not
        enough. This is exported as a public function mainly for the benefit of
        unit tests.
        """
        old = self.pages.get(page.site_relpath)
        if old is not None:
            log.warn("%s: replacing page %s", page, old)
        self.pages[page.site_relpath] = page
        self.pages_by_src_relpath[page.src.relpath] = page

        # Also group pages by tracked metadata
        for tracked in page.meta.keys() & self.tracked_metadata:
            self.pages_by_metadata[tracked].append(page)

    def add_test_page(self, feature: str, relpath, *args, meta=None, **kw) -> Page:
        """
        Add a page instantiated using the given feature for the purpose of unit
        testing.

        :return: the Page added
        """
        if meta is None:
            meta = {}
        for k, v in self._settings_to_meta().items():
            meta.setdefault(k, v)

        # Populate directory metadata for all path components
        path = relpath
        while True:
            path = os.path.dirname(path)
            if path not in self.dir_meta:
                self.dir_meta[path] = self._settings_to_meta()
            if not path:
                break

        page = self.features[feature].build_test_page(relpath, *args, meta=meta, **kw)
        if not page.is_valid():
            raise RuntimeError("Tried to add an invalid test page")
        self.add_page(page)
        return page

    def analyze(self):
        """
        Iterate through all Pages in the site to build aggregated content like
        taxonomies and directory indices.

        Call this after all Pages have been added to the site.
        """
        # Add missing pages_by_metadata entries in case no matching page were
        # found for some of them
        for key in self.tracked_metadata:
            if key not in self.pages_by_metadata:
                self.pages_by_metadata[key] = []

        # Call finalize hook on features
        for feature in self.features.ordered():
            feature.finalize()

    def slugify(self, text):
        """
        Return the slug version of an arbitrary string, that can be used as an
        url component or file name.
        """
        from slugify import slugify
        return slugify(text)

    def localized_timestamp(self, ts):
        return pytz.utc.localize(
                        datetime.datetime.utcfromtimestamp(ts)
                    ).astimezone(self.timezone)

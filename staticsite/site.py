from __future__ import annotations

import datetime
import logging
import os
import re
from functools import cached_property
from typing import TYPE_CHECKING, Any, Generator, Optional, Sequence, Union

import dateutil.parser
import pytz

from . import fields, fstree
from .cache import Caches, DisabledCaches
from .file import File
from .settings import Settings
from .utils import timings

if TYPE_CHECKING:
    from .archetypes import Archetypes
    from .node import Node
    from .page import Page
    from .theme import Theme

log = logging.getLogger("site")


class Path(tuple[str]):
    """
    Path in the site, split into components
    """
    re_pathsep = re.compile(re.escape(os.sep) + "+")

    @property
    def head(self) -> str:
        """
        Return the first element in the path
        """
        return self[0]

    @property
    def tail(self) -> Path:
        """
        Return the Path after the first element
        """
        # TODO: check if it's worth making this a cached_property
        return Path(self[1:])

    @property
    def dir(self) -> Path:
        """
        Return the path with all components except last
        """
        return Path(self[:-1])

    @property
    def name(self) -> str:
        """
        Return the last component of the path
        """
        return self[-1]

    @classmethod
    def from_string(cls, path: str) -> "Path":
        """
        Split a string into a path
        """
        return cls(cls.re_pathsep.split(path.strip(os.sep)))


class SiteElement(fields.FieldContainer):
    """
    Common fields for site elements
    """
    site_name = fields.Inherited[fields.FieldContainer, str](doc="""
        Name of the site. If missing, it defaults to the title of the toplevel index
        page. If missing, it defaults to the name of the content directory.
    """)

    site_url = fields.Inherited[fields.FieldContainer, str](doc="""
        Base URL for the site, used to generate an absolute URL to the page.
    """)

    author = fields.Inherited[fields.FieldContainer, str](doc="""
        A string with the name of the author for this page.

        SITE_AUTHOR is used as a default if found in settings.

        If not found, it defaults to the current user's name.
    """)

    template_copyright = fields.TemplateInherited[fields.FieldContainer](doc="""
        jinja2 template to use to generate `copyright` when it is not explicitly set.

        The template context will have `page` available, with the current page. The
        result of the template will not be further escaped, so you can use HTML markup
        in it.

        If missing, defaults to `"© {{meta.date.year}} {{meta.author}}"`
    """)

    template_title = fields.TemplateInherited[fields.FieldContainer](doc="""
        jinja2 template to use to generate `title` when it is not explicitly set.

        The template context will have `page` available, with the current page.
        The result of the template will not be further escaped, so you can use
        HTML markup in it.
    """)

    template_description = fields.TemplateInherited[fields.FieldContainer](doc="""
        jinja2 template to use to generate `description` when it is not
        explicitly set.

        The template context will have `page` available, with the current page.
        The result of the template will not be further escaped, so you can use
        HTML markup in it.
    """)

    asset = fields.Inherited[fields.FieldContainer, bool](doc="""
        If set to True for a file (for example, by a `file:` pattern in a directory
        index), the file is loaded as a static asset, regardless of whether a feature
        would load it.

        If set to True in a directory index, the directory and all its subdirectories
        are loaded as static assets, without the interventions of features.
    """)

    def lookup_page(self, path: Path) -> Optional[Page]:
        """
        Find a page by given a path starting from this site element

        The final path component can match:
        * a node name
        * the basename of a page's src_relpath
        * the rendered file name
        """
        raise NotImplementedError(f"{self.__class__.__name__}.lookup_page() not implemented")

    def resolve_path(self, target: Union[str, "Page"], static=False) -> "Page":
        """
        Return a Page from the site, given a source or site path relative to
        this page.

        The path is resolved relative to this node, and if not found, relative
        to the parent node, and so on until the top.
        """
        from .page import Page, PageNotFoundError

        if isinstance(target, Page):
            return target

        path = Path.from_string(target)

        if target.startswith("/"):
            if static:
                root = self.site.static_root
            else:
                root = self.site.root
            page = root.lookup_page(path)
        else:
            page = self.lookup_page(path)

        if page is None:
            raise PageNotFoundError(f"cannot resolve {target!r} relative to {self!r}")
        else:
            return page


class Site:
    """
    A staticsite site.

    This class tracks all resources associated with a site.
    """
    # Identifiers for steps of the site loading
    LOAD_STEP_INITIAL = 0
    LOAD_STEP_FEATURES = 1
    LOAD_STEP_THEME = 2
    LOAD_STEP_DIRS = 3
    LOAD_STEP_CONTENTS = 4
    LOAD_STEP_ORGANIZE = 5
    LOAD_STEP_GENERATE = 6
    LOAD_STEP_CROSSREFERENCE = 7
    LOAD_STEP_ALL = LOAD_STEP_CROSSREFERENCE

    def __init__(self, settings: Optional[Settings] = None, generation_time: Optional[datetime.datetime] = None):
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

        # Site time zone
        if settings.TIMEZONE is None:
            from dateutil.tz import tzlocal
            self.timezone = tzlocal()
        else:
            self.timezone = pytz.timezone(settings.TIMEZONE)

        # Current datetime
        self.generation_time: datetime.datetime
        if generation_time is not None:
            self.generation_time = generation_time.astimezone(self.timezone)
        else:
            self.generation_time = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(self.timezone)

        # Filesystem trees scanned by the site
        self.fstrees: dict[str, fstree.Tree] = {}

        # Root node of the site
        self.root: Node

        # Root node for the static contents of the site
        self.static_root: Node

        # Last load step performed
        self.last_load_step = self.LOAD_STEP_INITIAL

        # Set to True when feature constructors have been called
        self.stage_features_constructed = False

        # Theme used to render pages
        self._theme = None

        # Feature implementation registry
        self.features = Features(self)

        # Build cache repository
        self.caches: Union[Caches, DisabledCaches]
        if self.settings.CACHE_REBUILDS:
            if os.access(self.settings.PROJECT_ROOT, os.W_OK):
                self.caches = Caches(os.path.join(self.settings.PROJECT_ROOT, ".staticsite-cache"))
            else:
                log.warn("%s: directory not writable: disabling caching", self.settings.PROJECT_ROOT)
                self.caches = DisabledCaches()
        else:
            self.caches = DisabledCaches()

        # Content root for the website
        self.content_root = os.path.normpath(os.path.join(self.settings.PROJECT_ROOT, self.settings.CONTENT))

        # Cache with last build information
        self.build_cache = self.caches.get("build")

        # Source page footprints from a previous build
        self.previous_source_footprints: dict[str, dict[str, Any]]

        # Pages for which we should call Page.crossreference() at the beginning of the crossreference stage
        self.pages_to_crossreference: set[Page] = set()

    @cached_property
    def theme(self) -> Theme:
        """
        Return the Theme object for this site
        """
        if self._theme is None:
            raise RuntimeError("Site.theme called before the theme was loaded")
        return self._theme

    def clear_footprints(self):
        """
        Clear the previous-build page footprints.

        This is used when something failed during a build, and the build
        directory is left in an inconsistent state
        """
        self.footprints = {}
        self.build_cache.put("footprints", self.footprints)

    def save_footprints(self):
        """
        Save the current set of page footprints as reference for a future build

        This is used after a build completed successfully, to allow incremental
        future builds
        """
        self.footprints = {
            page.src.relpath: page.footprint for page in self.iter_pages(source_only=True)
        }
        self.build_cache.put("footprints", self.footprints)
        for feature in self.features.ordered():
            self.build_cache.put(f"footprint_{feature.name}", feature.get_footprint())

    def deleted_source_pages(self) -> Sequence[str]:
        """
        Return a sequence with the source relpaths of pages deleted since the
        last run
        """
        # Entries are popped from previous_source_footprints while pages are
        # loaded, so if any remain it means that those pages have been deleted
        return self.previous_source_footprints.keys()

    def iter_pages(self, static: bool = True, source_only: bool = False) -> Generator[Page, None, None]:
        """
        Iterate all pages in the site
        """
        prune: tuple[Node, ...]
        if static:
            prune = ()
        elif (self.root != self.static_root):
            prune = (self.static_root,)
        else:
            prune = ()
        yield from self.root.iter_pages(prune=prune, source_only=source_only)

    @cached_property
    def archetypes(self) -> "Archetypes":
        """
        Archetypes defined in the site
        """
        from .archetypes import Archetypes
        if self.settings.PROJECT_ROOT is None:
            raise RuntimeError("PROJECT_ROOT is not set and cannot be inferred")
        return Archetypes(self, os.path.join(self.settings.PROJECT_ROOT, "archetypes"))

    def load_features(self):
        """
        Load default features
        """
        self.features.load_default_features()
        # We can now load source files footprint, before theme loads assets
        self.previous_source_footprints = self.build_cache.get("footprints")
        if self.previous_source_footprints is None:
            self.previous_source_footprints = {}

    def load_theme(self):
        """
        Load a theme from the given directory.

        This needs to be called once (and only once) before analyze() is
        called.
        """
        from .theme import Theme

        if self._theme is not None:
            raise RuntimeError(
                    F"load_theme called while a theme was already loaded from {self._theme.root}")

        if isinstance(self.settings.THEME, str):
            self._theme = Theme.create(self, self.settings.THEME)
        else:
            # Pick the first valid theme directory
            candidate_themes = self.settings.THEME
            if isinstance(candidate_themes, str):
                candidate_themes = (candidate_themes,)
            self._theme = Theme.create_legacy(self, candidate_themes)

        self._theme.load()

        # We now have the final feature list, we can load old feature footprints
        for feature in self.features.ordered():
            footprint = self.build_cache.get(f"footprint_{feature.name}")
            feature.set_previous_footprint(footprint if footprint is not None else {})

    def _settings_to_meta(self) -> dict[str, Any]:
        """
        Build directory metadata based on site settings
        """
        res = {
            "template_copyright": "© {{page.meta.date.year}} {{page.meta.author}}",
        }
        if self.settings.SITE_URL:
            res["site_url"] = self.settings.SITE_URL
        if self.settings.SITE_ROOT:
            res["site_path"] = os.path.normpath(os.path.join("/", self.settings.SITE_ROOT))
        else:
            res["site_path"] = "/"
        if self.settings.SITE_NAME:
            res["site_name"] = self.settings.SITE_NAME
        if self.settings.SITE_AUTHOR:
            res["author"] = self.settings.SITE_AUTHOR
        else:
            import getpass
            import pwd
            user = getpass.getuser()
            pw = pwd.getpwnam(user)
            res["author"] = pw.pw_gecos.split(",")[0]

        log.debug("Initial settings: %r", res)
        return res

    def scan_content(self):
        """
        Scan content root directories, building metadata for the directories in
        the site tree
        """
        from .node import RootNode
        if not self.stage_features_constructed:
            log.warn("scan_content called before site features have been loaded")

        if not os.path.exists(self.content_root):
            log.info("%s: content tree does not exist", self.content_root)
            return

        # Create root node
        self.root = self.features.get_node_class(RootNode)(self)

        # Create static root node
        self.static_root = self.root.at_path(Path.from_string(self.settings.STATIC_PATH))

        # Scan the main content filesystem
        src = File.with_stat("", os.path.abspath(self.content_root))
        tree = self.scan_tree(src, self._settings_to_meta(), toplevel=True)

        # Here we may have loaded more site-wide metadata from the root's index
        # page: incorporate them
        for k, v in tree.meta.items():
            if k in self.root._fields:
                setattr(self.root, k, v)

        if self.root.site_name is None:
            # If we still have no idea of site names, use the root directory's name
            self.root.site_name = os.path.basename(tree.src.abspath)

        # Scan asset trees from themes
        self._theme.scan_assets()

    def scan_tree(self, src: File, meta: dict[str, Any], toplevel: bool = False) -> fstree.Tree:
        """
        Scan the contents of the given directory, adding it to self.fstrees
        """
        tree: fstree.Tree
        if meta.get("asset"):
            tree = fstree.AssetTree(self, src)
        elif toplevel:
            tree = fstree.RootPageTree(self, src)
        else:
            tree = fstree.PageTree(self, src)
        tree.meta.update(meta)
        with tree.open_tree():
            tree.scan()
        self.fstrees[src.abspath] = tree
        return tree

    def load_content(self):
        """
        Load site page and assets from scanned content roots.
        """
        # Turn scanned filesytem information into site structure
        for abspath, tree in self.fstrees.items():
            # print(f"* tree {tree.src.relpath}")
            # tree.print()
            # Create root node based on site_path
            if (site_path := tree.meta.get("site_path")) and site_path.strip("/"):
                # print(f"Site.load_content populate at {site_path} from {tree.src.abspath}")
                node = self.root.at_path(Path.from_string(site_path))
            else:
                # print(f"Site.load_content populate at <root> from {tree.src.abspath}")
                node = self.root

            # Populate node from tree
            with tree.open_tree():
                tree.populate_node(node)

    def load(self, until: int = LOAD_STEP_ALL):
        """
        Load all site components
        """
        if until <= self.last_load_step:
            return

        if self.last_load_step < self.LOAD_STEP_FEATURES:
            with timings("Loaded default features in %fs"):
                self.load_features()
            self.last_load_step = self.LOAD_STEP_FEATURES
        if until <= self.last_load_step:
            return

        if self.last_load_step < self.LOAD_STEP_THEME:
            with timings("Loaded theme in %fs"):
                self.load_theme()
            self.last_load_step = self.LOAD_STEP_THEME
        if until <= self.last_load_step:
            return

        if self.last_load_step < self.LOAD_STEP_DIRS:
            with timings("Scanned contents in %fs"):
                self.scan_content()
            self.last_load_step = self.LOAD_STEP_DIRS
        if until <= self.last_load_step:
            return

        if self.last_load_step < self.LOAD_STEP_CONTENTS:
            with timings("Loaded contents in %fs"):
                self.load_content()
            self.last_load_step = self.LOAD_STEP_CONTENTS
        if until <= self.last_load_step:
            return

        if self.last_load_step < self.LOAD_STEP_ORGANIZE:
            with timings("Organized contents in %fs"):
                self._organize()
            self.last_load_step = self.LOAD_STEP_ORGANIZE
        if until <= self.last_load_step:
            return

        if self.last_load_step < self.LOAD_STEP_GENERATE:
            with timings("Generated new contents in %fs"):
                self._generate()
            self.last_load_step = self.LOAD_STEP_GENERATE
        if until <= self.last_load_step:
            return

        if self.last_load_step < self.LOAD_STEP_CROSSREFERENCE:
            with timings("Cross-referenced contents in %fs"):
                self._crossreference()
            self.last_load_step = self.LOAD_STEP_CROSSREFERENCE
        if until <= self.last_load_step:
            return

    def _organize(self):
        """
        Call features to organize the pages that have just been loaded from
        sources
        """
        # Call organize hook on features
        for feature in self.features.ordered():
            feature.organize()

    def _generate(self):
        """
        Call features to generate new pages
        """
        # Call generate hook on features
        for feature in self.features.ordered():
            feature.generate()

    def _crossreference(self):
        """
        Call features to cross-reference pages after the site structure has
        been finalized
        """
        # Call crossreference hook on selected pages
        for page in self.pages_to_crossreference:
            page.crossreference()

        # Call crossreference hook on features
        for feature in self.features.ordered():
            feature.crossreference()

    def slugify(self, text):
        """
        Return the slug version of an arbitrary string, that can be used as an
        url component or file name.
        """
        from slugify import slugify
        return slugify(text)

    def localized_timestamp(self, ts):
        return datetime.datetime.fromtimestamp(ts, tz=pytz.utc).astimezone(self.timezone)

    # TODO: support partial dates?
    re_isodate = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})(Z|\+\d{2}.*)$")

    def clean_date(self, date: Union[str, datetime.datetime]) -> datetime.datetime:
        """
        Return an aware datetime from a potential date value.

        Parse a date string, or make sure a datetime value is aware, or replace
        None with the current generation time
        """
        clean_date: datetime.datetime
        # Make sure we have a datetime
        if not isinstance(date, datetime.datetime):
            mo = self.re_isodate.match(date)
            if mo:
                if mo.group(2) == "Z":
                    clean_date = datetime.datetime.fromisoformat(mo.group(1)).replace(tzinfo=pytz.utc)
                else:
                    clean_date = datetime.datetime.fromisoformat(date)
            else:
                # TODO: log a fallback on dateutil?
                try:
                    clean_date = dateutil.parser.parse(date)
                except ValueError as e:
                    log.warn("cannot parse datetime %s: %s", date, e)
                    return self.generation_time
        else:
            clean_date = date

        # Make sure the datetime is aware
        if clean_date.tzinfo is None:
            if hasattr(self.timezone, "localize"):
                clean_date = self.timezone.localize(clean_date)
            else:
                clean_date = clean_date.replace(tzinfo=self.timezone)

        return clean_date

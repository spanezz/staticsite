from __future__ import annotations

import datetime
import logging
import os
import re
from functools import cached_property
from typing import TYPE_CHECKING, Any, Generator, Optional, Union

import dateutil.parser
import pytz

from . import fields, fstree
from .cache import Caches, DisabledCaches
from .file import File
from .settings import Settings
from .utils import timings

if TYPE_CHECKING:
    from .node import Node
    from .page import Page

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
    site_name = fields.Inherited(doc="""
        Name of the site. If missing, it defaults to the title of the toplevel index
        page. If missing, it defaults to the name of the content directory.
    """)

    site_url = fields.Inherited(doc="""
        Base URL for the site, used to generate an absolute URL to the page.
    """)

    author = fields.Inherited(doc="""
        A string with the name of the author for this page.

        SITE_AUTHOR is used as a default if found in settings.

        If not found, it defaults to the current user's name.
    """)

    template_copyright = fields.TemplateInherited(doc="""
        jinja2 template to use to generate `copyright` when it is not explicitly set.

        The template context will have `page` available, with the current page. The
        result of the template will not be further escaped, so you can use HTML markup
        in it.

        If missing, defaults to `"© {{meta.date.year}} {{meta.author}}"`
    """)

    template_title = fields.TemplateInherited(doc="""
        jinja2 template to use to generate `title` when it is not explicitly set.

        The template context will have `page` available, with the current page.
        The result of the template will not be further escaped, so you can use
        HTML markup in it.
    """)

    template_description = fields.TemplateInherited(doc="""
        jinja2 template to use to generate `description` when it is not
        explicitly set.

        The template context will have `page` available, with the current page.
        The result of the template will not be further escaped, so you can use
        HTML markup in it.
    """)

    asset = fields.Inherited(doc="""
        If set to True for a file (for example, by a `file:` pattern in a directory
        index), the file is loaded as a static asset, regardless of whether a feature
        would load it.

        If set to True in a directory index, the directory and all its subdirectories
        are loaded as static assets, without the interventions of features.
    """)


class RootNodeFields(metaclass=fields.FieldsMetaclass):
    """
    Extra fields for the root node
    """
    title = fields.Field(doc="""
        Title used as site name.

        This only makes sense for the root node of the site hierarchy, and
        takes the value from the title of the root index page. If set, and the
        site name is not set by other means, it is used to give the site a name.
    """)


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
    LOAD_STEP_ANALYZE = 5
    LOAD_STEP_ALL = LOAD_STEP_ANALYZE

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

        # Root directory of the site
        self.root: Node

        # Last load step performed
        self.last_load_step = self.LOAD_STEP_INITIAL

        # Set to True when feature constructors have been called
        self.stage_features_constructed = False

        # Set to True when content directories have been scanned
        self.stage_content_directory_scanned = False

        # Set to True when content directories have been loaded
        self.stage_content_directory_loaded = False

        # Set to True when pages have been analyzed
        self.stage_pages_analyzed = False

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
        self.content_root = os.path.normpath(os.path.join(self.settings.PROJECT_ROOT, self.settings.CONTENT))

        # Register well-known metadata

    def find_page(self, path: str):
        """
        Find a page by absolute path in the site
        """
        return self.root.resolve_path(path)

    def iter_pages(self, static: bool = True) -> Generator[Page, None, None]:
        """
        Iterate all pages in the site
        """
        if static:
            prune = ()
        else:
            prune = (
                self.root.lookup(Path.from_string(self.settings.STATIC_PATH)),
            )
        yield from self.root.iter_pages(prune=prune)

    @cached_property
    def archetypes(self) -> "archetypes.Archetypes":
        """
        Archetypes defined in the site
        """
        from .archetypes import Archetypes
        return Archetypes(self, os.path.join(self.settings.PROJECT_ROOT, "archetypes"))

    def load_theme(self):
        """
        Load a theme from the given directory.

        This needs to be called once (and only once) before analyze() is
        called.
        """
        from .theme import Theme

        if self.theme is not None:
            raise RuntimeError(
                    F"load_theme called while a theme was already loaded from {self.theme.root}")

        if isinstance(self.settings.THEME, str):
            self.theme = Theme.create(self, self.settings.THEME)
        else:
            # Pick the first valid theme directory
            candidate_themes = self.settings.THEME
            if isinstance(candidate_themes, str):
                candidate_themes = (candidate_themes,)
            self.theme = Theme.create_legacy(self, candidate_themes)

        self.theme.load()

    def _settings_to_meta(self) -> dict[str, Any]:
        """
        Build directory metadata based on site settings
        """
        res = {
            "template_copyright": "© {{meta.date.year}} {{meta.author}}",
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
        if not self.stage_features_constructed:
            log.warn("scan_content called before site features have been loaded")

        if not os.path.exists(self.content_root):
            log.info("%s: content tree does not exist", self.content_root)
            return

        # Create root node
        self.root = type("RootNode", (RootNodeFields, self.features.get_node_class(),), {})(self, "")

        # Scan the main content filesystem
        src = File.with_stat("", os.path.abspath(self.content_root))
        tree = self.scan_tree(src, self._settings_to_meta(), toplevel=True)

        # Here we may have loaded more site-wide metadata from the root's index
        # page: incorporate them
        self.root.update_fields(tree.meta)

        if self.root.site_name is None:
            # If we still have no idea of site names, use the root directory's name
            self.root.site_name = os.path.basename(tree.src.abspath)

        # Scan asset trees from themes
        self.theme.scan_assets()

        # Notify Features that contents have been scanned
        self.features.contents_scanned()

        self.stage_content_directory_scanned = True

    def scan_tree(self, src: File, meta: dict[str, Any], toplevel: bool = False) -> fstree.Tree:
        """
        Scan the contents of the given directory, adding it to self.fstrees
        """
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
        if not self.stage_content_directory_scanned:
            log.warn("load_content called before site features have been loaded")

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

            # print("Populated as:")
            # node.print()

        self.stage_content_directory_loaded = True

        # print("Final site structure:")
        # self.root.print()

    def load(self, until: int = LOAD_STEP_ALL):
        """
        Load all site components
        """
        if until <= self.last_load_step:
            return

        if self.last_load_step < self.LOAD_STEP_FEATURES:
            with timings("Loaded default features in %fs"):
                self.features.load_default_features()
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

        if self.last_load_step < self.LOAD_STEP_ANALYZE:
            with timings("Analyzed contents in %fs"):
                self._analyze()
            self.last_load_step = self.LOAD_STEP_ANALYZE
        if until <= self.last_load_step:
            return

    def is_page_ignored(self, page: Page) -> bool:
        """
        Check if this page should be ignored and not added to the site
        """
        if not self.settings.DRAFT_MODE and page.draft:
            log.info("%s: page is still a draft: skipping", page)
            return True

        return False

    def _analyze(self):
        """
        Iterate through all Pages in the site to build aggregated content like
        taxonomies and directory indices.

        Call this after all Pages have been added to the site.
        """
        if not self.stage_content_directory_loaded:
            log.warn("analyze called before loading site contents")

        # Call analyze hook on features
        for feature in self.features.ordered():
            feature.analyze()

        self.stage_pages_analyzed = True

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
        # Make sure we have a datetime
        if not isinstance(date, datetime.datetime):
            mo = self.re_isodate.match(date)
            if mo:
                if mo.group(2) == "Z":
                    date = datetime.datetime.fromisoformat(mo.group(1)).replace(tzinfo=pytz.utc)
                else:
                    date = datetime.datetime.fromisoformat(date)
            else:
                # TODO: log a fallback on dateutil?
                try:
                    date = dateutil.parser.parse(date)
                except ValueError as e:
                    log.warn("cannot parse datetime %s: %s", date, e)
                    return self.generation_time

        # Make sure the datetime is aware
        if date.tzinfo is None:
            if hasattr(self.timezone, "localize"):
                date = self.timezone.localize(date)
            else:
                date = date.replace(tzinfo=self.timezone)

        return date

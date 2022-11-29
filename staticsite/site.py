from __future__ import annotations

import datetime
import logging
import os
import re
import warnings
from functools import cached_property
from typing import TYPE_CHECKING, Optional, Union

import dateutil.parser
import pytz

from . import metadata, scan, structure
from .cache import Caches, DisabledCaches
from .file import File
from .metadata import Meta, Metadata
from .settings import Settings
from .utils import timings

if TYPE_CHECKING:
    from .page import Page

log = logging.getLogger("site")


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

        # Repository of metadata descriptions
        self.metadata = metadata.Registry(self)

        # Structure of pages in the site
        self.structure = structure.Structure(self)

        # Set to True when feature constructors have been called
        self.stage_features_constructed = False

        # Set to True when content directories have been scanned
        self.stage_content_directory_scanned = False

        # Set to True when content directories have been loaded
        self.stage_content_directory_loaded = False

        # Set to True when pages have been analyzed
        self.stage_pages_analyzed = False

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
        self.content_root = os.path.normpath(os.path.join(self.settings.PROJECT_ROOT, self.settings.CONTENT))

        # Register well-known metadata
        self.register_metadata(metadata.MetadataDefault("template", default="page.html", doc="""
Template used to render the page. Defaults to `page.html`, although specific
pages of some features can default to other template names.

Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).
"""))

        self.register_metadata(metadata.MetadataDate("date", doc="""
Publication date for the page.

A python datetime object, timezone aware. If the date is in the future when
`ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
--draft` to also consider draft pages.

If missing, the modification time of the file is used.
"""))

        self.register_metadata(metadata.MetadataInherited("site_name", doc="""
Name of the site. If missing, it defaults to the title of the toplevel index
page. If missing, it defaults to the name of the content directory.
"""))

        self.register_metadata(metadata.MetadataInherited("site_url", doc="""
Base URL for the site, used to generate an absolute URL to the page.
"""))

        self.register_metadata(metadata.Metadata("site_path", doc="""
Where a content directory appears in the site.

By default, is is the `site_path` of the parent directory, plus the directory
name.

If you are publishing the site at `/prefix` instead of the root of the domain,
override this with `/prefix` in the content root.
"""))

        self.register_metadata(metadata.MetadataDraft("draft", doc="""
If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.

It defaults to false, or true if `meta.date` is in the future.
"""))

        self.register_metadata(metadata.MetadataInherited("author", doc="""
            A string with the name of the author for this page.

            SITE_AUTHOR is used as a default if found in settings.

            If not found, it defaults to the current user's name.
        """))
        self.register_metadata(metadata.MetadataTemplateInherited("copyright", template="template_copyright",
                               doc="""
If `template_copyright` is set instead of `copyright`, it is a jinja2 template
used to generate the copyright information.

The template context will have `page` available, with the current page. The
result of the template will not be further escaped, so you can use HTML markup
in it.

If missing, defaults to `"© {{meta.date.year}} {{meta.author}}"`
"""))
        self.register_metadata(metadata.MetadataTemplateInherited("title", template="template_title", doc="""
The page title.

If `template_title` is set instead of `title`, it is a jinja2 template used to
generate the title. The template context will have `page` available, with the
current page. The result of the template will not be further escaped, so you
can use HTML markup
in it.

If omitted:

 * the first title found in the page contents is used.
 * in the case of jinaj2 template pages, the contents of `{% block title %}`,
   if present, is rendered and used.
 * if the page has no title, the title of directory indices above this page is
   inherited.
 * if still no title can be found, the site name is used as a default.
"""))
        self.register_metadata(metadata.MetadataTemplateInherited("description", template="template_description",
                               doc="""
The page description. If omitted, the page will have no description.

If `template_description` is set instead of `description`, it is a jinja2
template used to generate the description. The template context will have
`page` available, with the current page. The result of the template will not be
further escaped, so you can use HTML markup in it.
"""))

        self.register_metadata(Metadata("build_path", doc="""
Relative path in the build directory for the file that will be written
when this page gets rendered. For example, `blog/2016/example.md`
generates `blog/2016/example/index.html`.

If found in pages front matter, it is ignored, and is always computed at page
load time.
"""))

        self.register_metadata(metadata.MetadataInherited("asset", doc="""
If set to True for a file (for example, by a `file:` pattern in a directory
index), the file is loaded as a static asset, regardless of whether a feature
would load it.

If set to True in a directory index, the directory and all its subdirectories
are loaded as static assets, without the interventions of features.
"""))

        self.register_metadata(metadata.MetadataIndexed("indexed", doc="""
If true, the page appears in [directory indices](dir.md) and in
[page filter results](page_filter.md).

It defaults to true at least for [Markdown](markdown.md),
[reStructuredText](rst.rst), and [data](data.md) pages.
"""))

    @property
    def pages(self):
        """
        Compatibility accessor for structure.pages
        """
        warnings.warn("use site.structure.pages instead of site.pages", DeprecationWarning)
        return self.structure.pages

    @property
    def pages_by_metadata(self):
        """
        Compatibility accessor for structure.pages_by_metadata
        """
        warnings.warn("use site.structure.pages_by_metadata instead of site.pages_by_metadata", DeprecationWarning)
        return self.structure.pages_by_metadata

    @property
    def pages_by_src_relpath(self):
        """
        Compatibility accessor for structure.pages_by_src_relpath
        """
        warnings.warn(
            "use site.structure.pages_by_src_relpath instead of site.pages_by_src_relpath", DeprecationWarning)
        return self.structure.pages_by_src_relpath

    @property
    def tracked_metadata(self):
        """
        Compatibility accessor for structure.tracked_metadata
        """
        warnings.warn("use site.structure.tracked_metadata instead of site.tracked_metadata", DeprecationWarning)
        return self.structure.tracked_metadata

    def register_metadata(self, metadata: Metadata):
        """
        Add a well-known metadata description to the metadata registry.

        This can be called safely by feature constructors and `load_dir_meta`
        methods of features.

        After directory metadata have been loaded, this method should not be
        called anymore.
        """
        if self.stage_content_directory_scanned:
            log.warn("register_metadata called after content directory has been scanned")
        self.metadata.add(metadata)

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

    def _settings_to_meta(self, meta: Meta):
        """
        Build directory metadata based on site settings
        """
        meta["template_copyright"] = "© {{meta.date.year}} {{meta.author}}"
        if self.settings.SITE_URL:
            meta["site_url"] = self.settings.SITE_URL
        if self.settings.SITE_ROOT:
            meta["site_path"] = os.path.normpath(os.path.join("/", self.settings.SITE_ROOT))
        else:
            meta["site_path"] = "/"
        if self.settings.SITE_NAME:
            meta["site_name"] = self.settings.SITE_NAME
        if self.settings.SITE_AUTHOR:
            meta["author"] = self.settings.SITE_AUTHOR
        else:
            import getpass
            import pwd
            user = getpass.getuser()
            pw = pwd.getpwnam(user)
            meta["author"] = pw.pw_gecos.split(",")[0]

        log.debug("Initial settings: %r", meta)

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

        self._settings_to_meta(self.structure.root.meta)
        src = File.with_stat("", os.path.abspath(self.content_root))
        self.scan_tree(src)
        # Here we may have loaded more site-wide metadata from the root's index
        # page: incorporate them
        # if self.structure.root.page:
        #     self.meta.update(self.structure.root.page.meta.values)
        self.theme.scan_assets()
        self.stage_content_directory_scanned = True

    def scan_tree(self, src: File, root: Optional[structure.Node] = None):
        """
        Scan the contents of the given directory, mounting them under the given
        site_path
        """
        if root is None:
            root = self.structure.root
        scan.scan_tree(self, src, node=root)

    def load_content(self):
        """
        Load site page and assets from scanned content roots.
        """
        if not self.stage_content_directory_scanned:
            log.warn("load_content called before site features have been loaded")

        # for root in self.content_roots:
        #     with open_dir_fd(root.src.abspath) as dir_fd:
        #         root.load(dir_fd)

        self.stage_content_directory_loaded = True

    def load(self):
        """
        Load all site components
        """
        with timings("Loaded default features in %fs"):
            self.features.load_default_features()
        with timings("Loaded theme in %fs"):
            self.load_theme()
        with timings("Scanned contents in %fs"):
            self.scan_content()
        with timings("Loaded contents in %fs"):
            self.load_content()

    def is_page_ignored(self, page: Page) -> bool:
        """
        Check if this page should be ignored and not added to the site
        """
        from .page import PageValidationError
        try:
            page.validate()
        except PageValidationError as e:
            log.warn("%s: skipping page: %s", e.page, e.msg)
            return True

        if not self.settings.DRAFT_MODE and page.meta["draft"]:
            log.info("%s: page is still a draft: skipping", page)
            return True

        return False

    def analyze(self):
        """
        Iterate through all Pages in the site to build aggregated content like
        taxonomies and directory indices.

        Call this after all Pages have been added to the site.
        """
        if not self.stage_content_directory_loaded:
            log.warn("analyze called before loading site contents")

        # Run metadata on_analyze functions
        for page in self.structure.pages.values():
            if page.meta.get("asset", False):
                continue
            self.metadata.on_analyze(page)

        self.structure.analyze()

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

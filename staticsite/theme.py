from __future__ import annotations

import datetime
import logging
import os
import re
from collections import defaultdict
from collections.abc import Callable, MutableMapping, Sequence
from typing import TYPE_CHECKING, Any

import jinja2
import jinja2.sandbox
import markupsafe

from . import toposort
from .file import File
from .page import ImagePage, Page, PageNotFoundError
from .utils import front_matter
from .utils.arrange import arrange

if TYPE_CHECKING:
    from .page import Pages
    from .site import Site

log = logging.getLogger("theme")


class ThemeNotFoundError(Exception):
    pass


class Loader:
    """
    Theme loader, resolving theme dependency chains
    """

    def __init__(self, search_paths: Sequence[str]):
        # Sequence of search paths to use to resolve theme names
        self.search_paths = search_paths
        # Configurations by name
        self.configs: dict[str, dict[str, Any]] = {}
        # Dependency graph of themes
        self.deps: dict[str, set[str]] = defaultdict(set)

    def load(self, name: str) -> list[dict[str, Any]]:
        """
        Load the configuration of the given theme and all its dependencies.

        Return the list of all the resulting configurations in topological
        order, with the bottom-most dependency first and the named theme last
        """
        self.load_configs(name)
        sorted_names = toposort.sort(self.deps)
        return [self.configs[name] for name in sorted_names]

    def load_legacy(self, path: str) -> list[dict[str, Any]]:
        """
        Same as load, but start with a path to an initial theme
        """
        name = os.path.basename(path)
        config = self.load_config(path, name)
        self.configs[name] = config
        self.deps[name]

        for parent in config["extends"]:
            self.load_configs(parent)
            self.deps[name].add(parent)

        sorted_names = toposort.sort(self.deps)
        return [self.configs[name] for name in sorted_names]

    def load_configs(self, name: str) -> None:
        """
        Populate self.configs with the configuration of the named theme,
        preceded by all its dependencies
        """
        if name in self.configs:
            log.warning(
                "%s: dependency loop found between themes: ignoring dependency", name
            )
            return

        config = self.load_config(self.find_root(name), name)
        self.configs[name] = config
        self.deps[name]

        for parent in config["extends"]:
            self.load_configs(parent)
            self.deps[name].add(parent)

    def find_root(self, name: str) -> str:
        """
        Lookup the root directory of a theme by name
        """
        for path in self.search_paths:
            root = os.path.join(path, name)
            if os.path.isdir(root):
                return root

        raise ThemeNotFoundError(f"Theme {name!r} not found in {self.search_paths!r}")

    def load_config(self, root: str, name: str) -> dict[str, Any]:
        """
        Load the configuration for the given named theme
        """
        pathname = os.path.join(root, "config")
        if not os.path.isfile(pathname):
            config: dict[str, Any] = {}
        else:
            with open(pathname) as fd:
                fmt, config = front_matter.read_whole(fd)

        # Normalize 'extends' to a list of strings
        extends = config.get("extends")
        if extends is None:
            config["extends"] = []
        elif isinstance(extends, str):
            config["extends"] = [extends]

        # Theme name
        config["name"] = name

        # Absolute path to the root of the theme directory
        config["root"] = os.path.abspath(root)

        return config


class Jinja2TemplateLoader(jinja2.loaders.BaseLoader):
    re_content = re.compile(r"^content:(.+)")

    def __init__(self, theme: Theme):
        self.loader_content = jinja2.FileSystemLoader(theme.site.content_root)
        self.loader_theme = jinja2.FileSystemLoader(theme.template_lookup_paths)

    def get_loader(self, template: str) -> tuple[jinja2.loaders.BaseLoader, str]:
        mo = self.re_content.match(template)
        if mo:
            return self.loader_content, mo.group(1)
        else:
            return self.loader_theme, template

    def get_source(
        self, environment: jinja2.Environment, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        loader, name = self.get_loader(template)
        try:
            return loader.get_source(environment, name)
        except jinja2.TemplateNotFound:
            # re-raise the exception with the correct filename here.
            # (the one that includes the prefix)
            raise jinja2.TemplateNotFound(template)

    @jinja2.utils.internalcode
    def load(
        self,
        environment: jinja2.Environment,
        name: str,
        globals: MutableMapping[str, Any] | None = None,
    ) -> jinja2.Template:
        loader, local_name = self.get_loader(name)
        try:
            return loader.load(environment, local_name, globals)
        except jinja2.TemplateNotFound:
            # re-raise the exception with the correct filename here.
            # (the one that includes the prefix)
            raise jinja2.TemplateNotFound(name)

    def list_templates(self) -> list[str]:
        result = []
        for template in self.loader_theme.list_templates():
            result.append(template)
        for template in self.loader_content.list_templates():
            result.append("content:" + template)
        return result


class Theme:
    def __init__(self, site: Site, name: str, configs: list[dict[str, Any]]):
        # Site object
        self.site = site

        # Template name
        self.name = name

        # Configuration for this theme and all the dependencies, sorted from
        # the earliest dependency to the theme
        self.configs = configs

        # Jinja2 Environment
        self.jinja2: jinja2.Environment

        # Compute template lookup paths
        self.template_lookup_paths: list[str] = []
        for config in reversed(self.configs):
            self.template_lookup_paths.append(config["root"])
        log.info("%s: template lookup paths: %r", self.name, self.template_lookup_paths)

        # Compute feature directories
        self.feature_dirs = []
        for config in self.configs:
            features_dir = os.path.join(config["root"], "features")
            if os.path.isdir(features_dir):
                self.feature_dirs.append(features_dir)
        log.info("%s: feature directories: %r", self.name, self.feature_dirs)

        # Compute system asset names
        self.system_assets = set(self.site.settings.SYSTEM_ASSETS)
        for config in self.configs:
            self.system_assets.update(config.get("system_assets", ()))
        log.info("%s: system assets: %r", self.name, self.system_assets)

        # Compute theme static asset dirs
        self.theme_static_dirs = []
        for config in self.configs:
            theme_static = os.path.join(config["root"], "static")
            if os.path.isdir(theme_static):
                self.theme_static_dirs.append(theme_static)
        log.info("%s: theme static directories: %r", self.name, self.theme_static_dirs)

        # Merge theme metadata
        meta_keys = frozenset(("image_sizes",))
        self.meta: dict[str, Any] = {}
        for config in self.configs:
            for key in config.keys() & meta_keys:
                self.meta[key] = config[key]

    @classmethod
    def create(
        cls, site: Site, name: str, search_paths: Sequence[str] | None = None
    ) -> Theme:
        """
        Create a Theme looking up its name in the theme search paths
        """
        if site.settings.PROJECT_ROOT is None:
            raise RuntimeError("PROJECT_ROOT is None")

        if search_paths is None:
            search_paths = [
                os.path.join(site.settings.PROJECT_ROOT, path)
                for path in site.settings.THEME_PATHS
            ]
        loader = Loader(search_paths)
        return cls(site, name, loader.load(name))

    @classmethod
    def create_legacy(cls, site: Site, paths: Sequence[str]) -> Theme:
        """
        Create a theme from a list of possible theme paths
        """
        if site.settings.PROJECT_ROOT is None:
            raise RuntimeError("PROJECT_ROOT is None")

        loader = Loader(site.settings.THEME_PATHS)

        for root in paths:
            root = os.path.join(site.settings.PROJECT_ROOT, root)
            if os.path.isdir(root):
                return cls(site, os.path.basename(root), loader.load_legacy(root))

        raise ThemeNotFoundError(f"Theme not found in {paths!r}")

    def load(self) -> None:
        # Load feature plugins from the theme directories
        self.site.features.load_feature_dir(self.feature_dirs)
        self.site.features.commit()
        self.site.stage_features_constructed = True

        env_cls: type[jinja2.Environment]
        # Jinja2 template engine
        if self.site.settings.JINJA2_SANDBOXED:
            env_cls = jinja2.sandbox.ImmutableSandboxedEnvironment
        else:
            env_cls = jinja2.Environment

        self.jinja2 = env_cls(
            loader=Jinja2TemplateLoader(self),
            autoescape=True,
        )

        # Add settings to jinja2 globals
        for x in dir(self.site.settings):
            if not x.isupper():
                continue
            self.jinja2.globals[x] = getattr(self.site.settings, x)

        self.jinja2.globals["site"] = self.site
        self.jinja2.globals["regex"] = re.compile

        # Install site's functions into the jinja2 environment
        self.jinja2.globals.update(
            has_page=self.jinja2_has_page,
            url_for=self.jinja2_url_for,
            page_for=self.jinja2_page_for,
            site_pages=self.jinja2_site_pages,
            img_for=self.jinja2_img_for,
            now=self.site.generation_time,
            next_month=(
                self.site.generation_time.replace(day=1) + datetime.timedelta(days=40)
            ).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        )

        self.jinja2.filters["datetime_format"] = self.jinja2_datetime_format
        self.jinja2.filters["next_month"] = self.jinja2_next_month
        self.jinja2.filters["basename"] = self.jinja2_basename
        self.jinja2.filters["arrange"] = self.jinja2_arrange

        # Add feature-provided globals and filters
        for feature in self.site.features.ordered():
            self.jinja2.globals.update(feature.j2_globals)
            self.jinja2.filters.update(feature.j2_filters)

    def scan_assets(self) -> None:
        """
        Load static assets
        """
        # Load system assets from site settings and theme configurations
        for name in self.system_assets:
            root = os.path.join("/usr/share/javascript", name)
            if not os.path.isdir(root):
                log.warning("%s: system asset directory not found", root)
                continue
            src = File.with_stat(name, root)
            self.site.scan_asset_tree(
                src=src,
                node=self.site.static_root.asset_child(name, src=src),
            )

        # Load assets from theme directories
        for path in self.theme_static_dirs:
            self.site.scan_asset_tree(
                src=File.with_stat("", os.path.abspath(path)),
                node=self.site.static_root,
            )

    def jinja2_basename(self, val: str) -> str:
        return os.path.basename(val)

    @jinja2.pass_context
    def jinja2_datetime_format(
        self,
        context: jinja2.runtime.Context,
        dt: str | datetime.datetime,
        format: str | None = None,
    ) -> str:
        if not isinstance(dt, datetime.datetime):
            import dateutil.parser

            dt = dateutil.parser.parse(dt)
        if format is None or format == "iso8601":
            from .utils import format_date_iso8601

            return format_date_iso8601(dt)
        elif format in ("rss2", "rfc822"):
            from .utils import format_date_rfc822

            return format_date_rfc822(dt)
        elif format in ("atom", "rfc3339"):
            from .utils import format_date_rfc3339

            return format_date_rfc3339(dt)
        elif format == "w3cdtf":
            from .utils import format_date_w3cdtf

            return format_date_w3cdtf(dt)
        elif format[0] == "%":
            return dt.strftime(format)
        else:
            log.warning(
                "%s+%s: invalid datetime format %r requested",
                context.parent["page"].src.relpath,
                context.name,
                format,
            )
            return f"(unknown datetime format {format})"

    @jinja2.pass_context
    def jinja2_next_month(
        self, context: jinja2.runtime.Context, dt: Any
    ) -> datetime.date | datetime.datetime:
        if isinstance(dt, str):
            import dateutil.parser

            dt = dateutil.parser.parse(dt)

        if isinstance(dt, datetime.datetime):
            return (dt.replace(day=1) + datetime.timedelta(days=40)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
        elif isinstance(dt, datetime.date):
            return (dt.replace(day=1) + datetime.timedelta(days=40)).replace(day=1)
        else:
            raise RuntimeError(
                f"{context.parent['page']}+{context.name}: invalid datetime {dt!r} of type {type(dt)}:"
                " accepted are str, datetime, date"
            )

    @jinja2.pass_context
    def jinja2_has_page(self, context: jinja2.runtime.Context, arg: str) -> bool:
        cur_page = context.get("page")
        try:
            cur_page.resolve_path(arg)
        except PageNotFoundError:
            return False
        else:
            return True

    @jinja2.pass_context
    def jinja2_page_for(self, context: jinja2.runtime.Context, arg: str | Page) -> Page:
        """
        Generate a URL for a page, specified by path or with the page itself
        """
        if isinstance(arg, Page):
            return arg

        cur_page: Page | None = context.get("page")
        if cur_page is None:
            raise RuntimeError(
                f"{cur_page}+{context.name}: page_for({arg!r}): current page is not defined"
            )

        try:
            return cur_page.resolve_path(arg)
        except PageNotFoundError as e:
            raise RuntimeError(f"{cur_page}+{context.name}: {e}")

    @jinja2.pass_context
    def jinja2_url_for(
        self,
        context: jinja2.runtime.Context,
        arg: str | Page,
        absolute: bool = False,
        static: bool = False,
    ) -> str:
        """
        Generate a URL for a page, specified by path or with the page itself
        """
        cur_page: Page | None = context.get("page")
        # print(f"Theme.jinja2_url_for {cur_page=!r}")
        if cur_page is None:
            log.warning(
                "%s+%s: url_for(%s): current page is not defined",
                cur_page,
                context.name,
                arg,
            )
            return ""

        try:
            return cur_page.url_for(arg, absolute=absolute, static=static)
        except PageNotFoundError as e:
            log.warning("%s:%s: %s", cur_page, context.name, e)
            return ""

    @jinja2.pass_context
    def jinja2_site_pages(
        self, context: jinja2.runtime.Context, **kw: Any
    ) -> list[Page]:
        cur_page: Page | None = context.get("page")
        if cur_page is None:
            log.warning(
                "%s+%s: site_pages: current page is not defined", cur_page, context.name
            )
            return []

        return cur_page.find_pages(**kw)

    @jinja2.pass_context
    def jinja2_img_for(
        self,
        context: jinja2.runtime.Context,
        path: str | Page,
        type: str | None = None,
        absolute: bool = False,
        **attrs: Any,
    ) -> str:
        cur_page = context.get("page")
        if cur_page is None:
            log.warning(
                "%s+%s: img(%s): current page is not defined",
                cur_page,
                context.name,
                path,
            )
            return ""

        image_page = cur_page.resolve_path(path)
        if isinstance(image_page, ImagePage):
            res_attrs = image_page.get_img_attributes(type=type, absolute=absolute)
        else:
            log.warning(
                "%s: img src= resolves to %s which is not an image page",
                cur_page,
                image_page,
            )
            res_attrs = {"src": cur_page.url_for(image_page)}

        escape = markupsafe.escape
        res = ["<img"]
        for k, v in res_attrs.items():
            res.append(f" {escape(k)}='{escape(v)}'")
        res.append("></img>")
        return markupsafe.Markup("".join(res))

    def jinja2_arrange(
        self, pages: Pages | list[Page], *args: Any, **kw: Any
    ) -> list[Page]:
        from .page import Pages

        if isinstance(pages, Pages):
            return pages.arrange(*args, **kw)
        else:
            return arrange(pages, *args, **kw)

from __future__ import annotations

import importlib
import logging
import sys
from typing import Any, Optional, Sequence, Union

log = logging.getLogger("settings")


class Settings:
    # Root directory used to resolve relative path in settings
    # Default if None: the directory where the settings file is found
    PROJECT_ROOT: Optional[str]

    # Base URL for the site, used to generate absolute URLs
    SITE_URL: str

    # Root directory of the site in the URLs we generate.
    #
    # If you are publishing the site at /prefix instead of root of the domain,
    # override this with /prefix
    SITE_ROOT: str

    # Default site name. If None, use the title of the toplevel index
    SITE_NAME: Optional[str]

    # Default author of the site
    SITE_AUTHOR: Optional[str]

    # Directory with "archetypes" (templates used by ssite new)
    # If None, archetypes are not used by ssite new
    ARCHETYPES: str

    # Directory with the source content of the site
    # Default if None: PROJECT_ROOT
    CONTENT: Optional[str]

    # Directories where themes are looked for
    THEME_PATHS: Sequence[str]

    # Theme used to render the site.
    # For compatibility, if it is a sequence of strings, it is treated as a list of
    # full paths to theme directories to try in order
    THEME: Union[str, Sequence[str]]

    # Directory where the static site will be written by build
    # If None, require providing it explicitly to build
    OUTPUT: Optional[str]

    # Time zone used for timestamps on the site
    # (NONE defaults to the system configured timezone)
    TIMEZONE: Optional[str]

    # Editor used to edit new pages
    EDITOR: str

    # Command used to run the editor, as passed to subprocess.check_command.
    # Each list element is expanded with string.format. All settings are available
    # for expansion, and {name} is the absolute path of the file to edit.
    EDIT_COMMAND: Sequence[str]

    # extensions for python-markdown and their config used for this site
    MARKDOWN_EXTENSIONS: list[str]
    MARKDOWN_EXTENSION_CONFIGS: dict[str, Any]

    # List of asset directories included from /usr/share/javascript
    SYSTEM_ASSETS: Sequence[str]

    # If true, do not ignore pages with dates in the future
    DRAFT_MODE: bool

    # If True, store cached data to speed up rebuilds
    CACHE_REBUILDS: bool

    # Patterns (glob or regexps) that identify files in content directories that
    # are parsed as jinja2 templates
    JINJA2_PAGES: Sequence[str]

    # Set to false to disable running Jinja2 in a sandboxed environnment.
    # If you trust your site sources, it renders noticeably faster.
    JINJA2_SANDBOXED: bool

    # Languages used to build the site
    # For now, only the first one is used, and only its locale is used.
    LANGUAGES: Sequence[dict[str, Any]]

    # Path where theme static assets will be placed in built site
    # Override with "" to merge when with the rest of the contents
    STATIC_PATH: str

    def __init__(self, default_settings="staticsite.global_settings"):
        if default_settings is not None:
            self.add_module(importlib.import_module(default_settings))

    def as_dict(self):
        res = {}
        for setting in dir(self):
            if setting.isupper():
                res[setting] = getattr(self, setting)
        return res

    def add_module(self, mod):
        """
        Add uppercase settings from mod into this module
        """
        for setting in dir(mod):
            if setting.isupper():
                setattr(self, setting, getattr(mod, setting))

    def load(self, pathname):
        """
        Load settings from a python file, importing only uppercase symbols
        """
        orig_dwb = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            # http://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path

            # Seriously, this should not happen in the standard library. You do not
            # break stable APIs. You can extend them but not break them. And
            # especially, you do not break stable APIs and then complain that people
            # stick to 2.7 until its death, and probably after.
            if sys.version_info >= (3, 5):
                import importlib.util
                spec = importlib.util.spec_from_file_location("staticsite.settings", pathname)
                user_settings = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(user_settings)
            else:
                from importlib.machinery import SourceFileLoader
                user_settings = SourceFileLoader("staticsite.settings", pathname).load_module()
        finally:
            sys.dont_write_bytecode = orig_dwb

        self.add_module(user_settings)

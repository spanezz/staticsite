from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from typing import Any

# Default settings

# Root directory used to resolve relative path in settings
# Default if None: the directory where the settings file is found
PROJECT_ROOT: str | None = None

# Base URL for the site, used to generate absolute URLs
SITE_URL: str | None = None

# Root directory of the site in the URLs we generate.
#
# If you are publishing the site at /prefix instead of root of the domain,
# override this with /prefix
SITE_ROOT: str = "/"

# Default site name. If None, use the title of the toplevel index
SITE_NAME: str | None = None

# Default author of the site
SITE_AUTHOR: str | None = None

# Directory with "archetypes" (templates used by ssite new)
# If None, archetypes are not used by ssite new
ARCHETYPES: str = "archetypes"

# Directory with the source content of the site
# Default if None: PROJECT_ROOT
CONTENT: str | None = None

# Directories where themes are looked for
THEME_PATHS: Sequence[str] = [
    os.path.abspath(
        os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), "themes")
    ),
    "/usr/share/staticsite/themes",
]

# Theme used to render the site.
# For compatibility, if it is a sequence of strings, it is treated as a list of
# full paths to theme directories to try in order
THEME: str | Sequence[str] = "default"

# Directory where the static site will be written by build
# If None, require providing it explicitly to build
OUTPUT: str | None = None

# Time zone used for timestamps on the site
# (NONE defaults to the system configured timezone)
TIMEZONE: str | None = None

# Editor used to edit new pages
EDITOR: str = os.environ.get("EDITOR", "sensible-editor")

# Command used to run the editor, as passed to subprocess.check_command.
# Each list element is expanded with string.format. All settings are available
# for expansion, and {name} is the absolute path of the file to edit.
EDIT_COMMAND: Sequence[str] = ["{EDITOR}", "{name}", "+"]

# extensions for python-markdown and their config used for this site
MARKDOWN_EXTENSIONS = [
    "markdown.extensions.extra",
    "markdown.extensions.codehilite",
    "markdown.extensions.fenced_code",
]
MARKDOWN_EXTENSION_CONFIGS = {
    "markdown.extensions.extra": {
        "markdown.extensions.footnotes": {
            # See https://github.com/spanezz/staticsite/issues/13
            "UNIQUE_IDS": True,
        },
    },
}

# List of asset directories included from /usr/share/javascript
SYSTEM_ASSETS: Sequence[str] = []

# If true, do not ignore pages with dates in the future
DRAFT_MODE: bool = False

# If True, store cached data to speed up rebuilds
CACHE_REBUILDS: bool = True

# Patterns (glob or regexps) that identify files in content directories that
# are parsed as jinja2 templates
JINJA2_PAGES: Sequence[str] = ["*.html", "*.j2.*"]

# Set to false to disable running Jinja2 in a sandboxed environnment.
# If you trust your site sources, it renders noticeably faster.
JINJA2_SANDBOXED = True

# Languages used to build the site
# For now, only the first one is used, and only its locale is used.
LANGUAGES: Sequence[dict[str, Any]] = [
    {
        "locale": "C",
    },
]

# Path where theme static assets will be placed in built site
# Override with "" to merge when with the rest of the contents
STATIC_PATH = "static"

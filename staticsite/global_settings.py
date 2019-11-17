import os

# Root directory used to resolve relative path in site sources
PROJECT_ROOT = "."

# Root directory of the site in the URLs we generate.
#
# If you are publishing the site at /prefix instead of root of the domain,
# override this with /prefix
SITE_ROOT = "/"

# Default site name. Override it with your site name.
SITE_NAME = "Site name not set"

# Directory with "archetypes" (templates used by ssite new)
ARCHETYPES = "archetypes"

# Directory with the source content of the site
# Default: the project directory itself
CONTENT = "content"

# Theme used to render the site. A sequence of strings is tried in order.
# Default: the one installed in the system
THEME = ("/usr/share/doc/staticsite/example/theme/", "theme")

# Directory where the static site will be written by build
OUTPUT = "web"

# Time zone used for timestamps on the site
TIMEZONE = "UTC"

# Editor used to edit new pages
EDITOR = os.environ.get("EDITOR", "sensible-editor")

# Command used to run the editor, as passed to subprocess.check_command.
# Each list element is expanded with string.format. All settings are available
# for expansion, and {name} is the absolute path of the file to edit.
EDIT_COMMAND = ["{EDITOR}", "{name}", "+"]

# extensions for python-markdown and their config used for this site
MARKDOWN_EXTENSIONS = [
    "markdown.extensions.extra",
    "markdown.extensions.codehilite",
    "markdown.extensions.fenced_code",
]
MARKDOWN_EXTENSION_CONFIGS = {
    'markdown.extensions.extra': {
        'markdown.extensions.footnotes': {
            # See https://github.com/spanezz/staticsite/issues/13
            'UNIQUE_IDS': True,
        },
    },
}

# List of asset directories included from /usr/share/javascript
SYSTEM_ASSETS = []

# If true, do not ignore pages with dates in the future
DRAFT_MODE = False

# If True, store cached data to speed up rebuilds
CACHE_REBUILDS = True

# List of taxonomy names used on this site
TAXONOMIES = []

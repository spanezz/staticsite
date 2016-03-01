# Root directory of the site in the URLs we generate.
#
# If you are publishing the site at /prefix instead of root of the domain,
# override this with /prefix
SITE_ROOT = "/"

# Time zone used for timestamps on the site
TIMEZONE = "UTC"

# Path used to create new pages
NEW_PAGE = "blog/{time:%Y}/{slug}.md"

# Default format for generating front matter
FRONT_MATTER = "toml"

# Editor used to edit new pages
import os
EDITOR = os.environ.get("EDITOR", "sensible-editor")

# Command used to run the editor, as passed to subprocess.check_command
EDIT_COMMAND = ["{EDITOR}", "{name}"]

# settings.py: configuration for the site

Sites can provide a configuration file, called `settings.py` or
`.staticsite.py` by default, that is interpreted via Python similarly to what
happens in [Django](https://docs.djangoproject.com/en/1.9/topics/settings/).

Only uppercase values set in the configuration are used by staticsite, the rest
is ignored.

Default settings are defined in the module `staticsite/global_settings.py` and
overridden by `settings.py` or `.staticsite.py`.

## Common settings

* `PROJECT_ROOT`: If some settings use relative paths, they are assumed to be
  rooted in this path. Defaults to the directory where the settings file is
  found.


## Site contents

* `CONTENT`: Directory with the source content of the site. Defaults to
  `PROJECT_ROOT`
* `THEME`: Theme used to render the site. A sequence of strings is tried in
  order. Defaults to `("/usr/share/doc/staticsite/example/theme/", "theme")`
* `SYSTEM_ASSETS`: Names of static asset directories to add from
  `/usr/share/javascript`. Defaults to the empty list.


## Site-wide metadata

* `SITE_NAME`: Site name. It defaults to the title of the toplevel page.
* `SITE_AUTHOR`: default value for the [`author` metadata](metadata.md)
* `TIMEZONE`: Default timezone used for datetimes in site contents.
* `TAXONOMIES`: List of [taxonomy](taxonomies.md) names used on the site.
  Defaults to no taxonomies.
* `LANGUAGES`: List of dicts representing which languages to build the site
  for. Currently only the first entry is used, and it should contain a `locale`
  key with the locale to use to build the site. In the future this can grow
  into building multiple versions of the site for different languages.
  Defaults to `[{"locale": "C"}]`.


## `ssite build` settings

* `SITE_URL`: default value for the [`site_url` metadata](metadata.md).
* `SITE_ROOT`: default value for the [`site_root` metadata](metadata.md).
* `OUTPUT`: Directory where the output of `ssite build` will go. If not set,
  `ssite build` will ask for it.
* `DRAFT_MODE`: If True, do not ignore pages with dates in the future. Defaults
  to False, where pages with dates in the future are considered drafts and are
  not included in the site.
* `CACHE_REBUILDS`: If True, store cached data to speed up rebuilds. Defaults
  to True.
* `BUILD_COMMAND`: set to the name of the `ssite` command being run.
* `JINJA2_SANDBOXED`: disable jinja2 sandboxing, making it noticeably faster,
  but allowing template designer to inject insecure code. Turn it on if you can
  trust the authors of templates.


## `ssite new` settings

* `ARCHETYPES`: Directory where [archetypes](archetypes.md) used by `ssite new`
  are found
* `EDITOR`: editor command used by `ssite new` to edit new pages. Defaults to
  `$EDITOR` or `sensible-editor`.
* `EDIT_COMMAND`: Command used to run the editor, as passed to
  `subprocess.check_command`. Each list element is expanded with
  `string.format`, with all other settings values made available to the
  `format` template, plus `{name}` set to the absolute path of the file to
  edit. Defaults to `["{EDITOR}", "{name}", "+"]`


## Feature specific settings

* `JINJA2_PAGES`: see [jinja2 pages documentation](doc/jinja2.md)
* `MARKDOWN_EXTENSIONS` and `MARKDOWN_EXTENSION_CONFIGS`:
  see [markdown pages documentation](doc/markdown.md)


[Back to reference index](reference.md)

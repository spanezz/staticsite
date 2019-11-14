# staticsite user-relevant changes

# New in version 1.1

* Documented and consolidated the Features feature

# New in version 1.0

* Refactored codebase to introduce the concept of pluggable Features. Most
  staticsite features are now implemented as pluggable features, and new
  features can be provided with python modules placed in the
  `$THEMEDIR/features/` directory
* Implemented data pages, as yaml, toml, or json, that provide pure datasets.
  `data-$type.html` jinja2 templates can be used to render their contents.
* Speed up site rebuilds by caching intermediate markdown contents

# New in version 0.6

* Allow to filter by taxonomies in `site_pages()`
* New settings `SYSTEM_ASSETS` to list directories in `/usr/share/javascript`
  to include to site assets
* Generate unique IDs in footnotes by default. Thanks DonKult!
* Implement rendering raw JSON, YAML, or TOML data files

# New in version 0.5

* Fixed markdown syntax for link targets in `example/archetypes/links.md`

# New in version 0.4

* Pages with dates in the future are considered drafts not yet to be published.
  Added option --draft to include them in the rendering.
* Added `{{next_month}}` to the template variables.
* Default editor configuration appends a `+` to the command line to open the
  file with the cursor at the end.
* If the archetype does not need a title or a slug, the `-t` argument to `ssite
  serve` is optional and no title will be asked interactively.
* Documented how to use staticsite to blog a monthly collection of links.

# New in version 0.3

* Allow to point to .py configuration instead of project on command line.
  This means you can potentially have a farm of .py site descriptions pointing
  at various other directories in the file system.
* archetypes and output directory configurable in `settings.py`. See
  [settings.md](doc/settings.md) for details.
* Added `--theme`, `--content`, `--archetypes` and `--output` to command line
  to override the corresponding settings.
* Fixed a bug in taxonomy generation

# New in version 0.2

* Configurable site layout, using `CONTENT` and `THEME` in `settings.py`. See
  [the settings reference](doc/settings.md) for details.
* The example `settings.py` has been updated to use `content` for site
  contents, like [Hugo](https://gohugo.io) does.
* Directory indices: if in your contents you have `dir/foo.md` without
  `dir/index.md` or `dir/index.j2.html", then a directory index for dir will be
  generated automatically, showing links to all site pages in that directory.
* Documentation has been expanded and split into separate files under `doc/`
* New template function `taxonomies()` that returns a list of taxonomies. See
  [templates.md](doc/templates.md).
* New template filter `|basename` that returns the basename of a path. See
  [templates.md](doc/templates.md).

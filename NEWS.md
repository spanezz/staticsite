# staticsite user-relevant changes

# New in version 0.4

* Pages with dates in the future are considered drafts not yet to be published.
  Added option --draft to include them in the rendering.
* Added `{{next_month}}` to the template variables.

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

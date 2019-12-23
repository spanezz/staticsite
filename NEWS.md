# staticsite user-relevant changes

# New in version 1.3

* New [page metadata](doc/metadata.md): `author`, `site_name`, `site_url`, and
  `site_root`.
* The contents of a `.staticsite` file can also now be loaded from the
  `index.html`/`index.md`/`index.rst` file in the directory, if present. This
  is now the recommended way to set directory metadata
* If no title is set in the front matter of a jinja2 template page, it defaults
  to the rendered `{% block title %}`
* `site_name`, if not set, defaults to the title of the toplevel index page, if
  present
* `.taxonomy` files do not need to be listed in [`TAXONOMIES`
  settings](doc/settings.md) anymore: `TAXONOMIES` is now ignored in settings.
* Restructured theme directory organization. See Upgrade notes for details.
* Set `site_path` in a directory metadata to choose where that directory
  appears in the target site. This replaces
  [`settings.SITE_ROOT`](doc/settings.md), which now acts as a default
  `site_path` for the toplevel directory.

## Upgrade notes

### Templates

* If you used `SITE_NAME` or `site.site_name`, use `page.meta.site_name`
  instead
* `blog.html` is now in `lib/blog.html` in default theme, to make space for the
  intruction of a default blog page template.
* `tags.html` is now `taxonomy/taxonomy.html`
* `tag.html` is now `taxonomy/category.html`
* `tag-archive.html` is now `taxonomy/archive.html`


# New in version 1.2

* RestructuredText Feature, see <doc/rst.rst>, thanks to @valholl.
* Taxonomies:
    * Renamed `tags` feature to `taxonomy`
    * Taxonomies now need to be explicitly listed in settings as a `TAXONOMIES`
      list of taxonomy names. staticsite prints a warning if a `.taxonomy` file is
      found that is not listed in `TAXONOMIES`.
    * You can use `tags: tagname` as short for `tags: [tagname]` if you
      only have one tag
    * Significantly reengineered 'taxonomy' feature.
    * Taxonomy pages are now ordered by ascending dates. You need to reverse
      them in templates (you can use the [`|reverse` jinja2 filter](https://jinja.palletsprojects.com/en/2.10.x/templates/#reverse))
      if you want them sorted as newest first.
    * Series are now generated from any category: `series_tags` is now ignored.
    * Removed `series` feature, merged into `taxonomy`
* Page metadata:
    * `description` can now be used for page metadata.
    * `template_title` and `template_description`, if present while `title` and
      `description` are not, are rendered with jinja2. See [doc/metadata.md] for
      details.
    * `template` metadata can be used to choose a custom template to render the
      page, similar to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).
    * `indexed` (true or false) is used to tell if a page appears in a
      directory index and in [page filter](doc/page-filter.md) results.
* Themes:
    * Vendorized assets in `theme/static/` are now read by asset library name, as
      if `static/` were the same as `/usr/share/javascript/`. Now you need to refer
      to `/jquery/jquery.min.js` and `/bootstrap4/css/bootstrap.min.css` instead of
      `jquery.min.js` and `css/bootstrap.min.css`.
    * If a `config` file exists in the theme directory, it is loaded as
      yaml/json/toml (same as a page front matter) and used as theme configuration
    * `static_assets` in theme configuration can be used to load assets from
      `/usr/share/javascript`
    * Turned `inline_pages.html` template into a `blog.html` macro library for
      blogs and category pages.
* Jinja2 pages
    * New setting [`JINJA2_PAGES`](doc/jinja2.md): now `*.html` pages are
      considered jinja2 templates by default.
    * Renamed `j2` feature to `jinja2`
* Content loading
    * A `.staticsite` file in a content directory is read as directory metadata,
      and can be used to provide metadata to `.j2.html` pages. See
      <doc/contents.md> for details.
    * Static assets loaded by the theme have been moved to `static/` in the
      rendered site, to avoid cluttering the rest of the contents. Referring to
      them in `url_for` in templates has not changed.
    * Set `asset` to true for a file in [`.staticsite` directory metadata](doc/contents.md),
      to force loading it as a static asset.
    * Allow marking entire subdirectories as assets in
      [directory metadata](doc/contents.md).
    * Try harder to localize timestamps as the configured site TIMEZONE.
* Added a `ssite show` command to open a directory in a browser without loading
  possibly unsafe settings.
* When run without a `settings.py`, take more defaults from repo mode. This
  makes running staticfile or arbitrary directories quite useful, and similar
  to viewing a repository on GitLab/GitHub.
* Improved logging in case of jinja2 errors. Use --debug to see a full
  stacktrace.
* Instantiate Feature classes in dependency order: this allows a feature
  constructor to register hooks with another one.
* Added syndication feature (see <doc/syndication.md>) to simplify generation
  of RSS and Atom feeds
* Added `ssite dump_meta` to page information as available to templates
* One can now match pages by regexp and not just by glob. See
  <doc/page-filter.md>.
* Cleaned up reference documentation.
* Allow selecting a language code for rendering. See `LANGUAGES` in [settings](doc/settings.md).
* Added `BUILD_COMMAND` [setting](doc/settings.md).
* Removed compatibility `Feature.load_dir` method. The old `try_load_page`
  method is no longer supported. Now a feature that does not load files does
  not waste time during content loading.
* [New `pages` feature](doc/pages.md) that allows defining a page filter in a
  `pages` metadata element, and then set `page.meta.pages` to a list of the
  matching pages. This can be used to simplify templates, so that with only one
  page filter one can control both the syndication and the page listing aspect
  of a blog page.
* [New `arrange()` template filter](doc/templates.md) to do efficient sorted
  sampling from a list of pages.
* `ssite edit`: when paginating results, an empty input goes to the next page
* cleanup and documented [directory index](doc/dir.md) feature
* `page.meta.alias` is honored for all page types
* `page.meta.template` is honored for all page types
* Started [developers documentation](doc/devel/README.md)
* Started [usage HOWTO documentation](doc/howto/README.md)
* Switch to [jinja2 sandboxed environment](https://jinja.palletsprojects.com/en/2.10.x/sandbox/)
  by default. Site [settings](doc/settings.md) can turn it off, which is ok
  because `settings.py` is a point where arbitrary code can be injected. This
  means that you now only have to secure access to `settings.py`, and can be a
  bit more free with allowing others to participate in the site development.
  Also, you need to use `ssite show`, and *not* `ssite serve`, to preview
  potentially untrusted sites: `ssite show` will not load a `settings.py`.

## Upgrade notes

### Taxonomies

* If you use taxonomies, explicitly list them in the new `TAXONOMIES`
  setting.
* `item_name` in a `.taxonomy` file does not have a special meaning anymore,
  and templates can still find it in the taxonomy page metadata
* `output_dir` in a `.taxonomy` file is now ignored, and the taxonomy pages
  will be in a directory with the same name as the file, without extension
* `tags.html`, `tag.html`, and `tag-archive.html` templates need updating: see
  the versions in `example/theme` for an updated example
* `series_tags` is now ignored
* The `series` feature is merged into `tags`: add a `series` taxonomy to keep using
  the `series` metadata in pages
* You may need to update the series rendering part of your templates: see
  [the series documentation](doc/series.md) and the `page.html` example template
  for details and an example.
* In templates, use `page.meta.pages` instead of `page.pages`

### Settings

* `PROJECT_ROOT` setting now defaults to `None` instead of `.`, and if None will
  be filled using the directory where the settings file is found, or the
  current directory otherwise. The resulting behaviour should be in practice
  very similar to the previous `.` setting.
* `TIMEZONE` setting now defaults to the system or user timezone instead of
  `UTC`
* `CONTENT` setting now defaults to `PROJECT_ROOT` instead of `content`. Set
  it to `content` explicitly if you depend on the previous value
* `OUTPUT` setting now defaults to `None` instead of `web`, and `ssite build`
  will ask you to set it or provide a `--output` option. Set it to `web`
  explicitly if you depend on the previous value
* `SITE_NAME` setting now defaults to `None` instead of `Site name not set`,
  and will be filled with the title of the toplevel index page, or the basename
  of the toplevel content directory if the toplevel index page has not title
  set or is autogenerated.

### Command line

* Running `ssite serve` on a random repository cloned off the internet can
  expose you to arbitrary code execution if the project includes a
  `.staticsite.py` settings file: use `ssite show` instead. Use `ssite serve`
  for authoring your own websites, whose settings you control.

### Pages

* `.html` files are now parsed as jinja2 templates by default. If you have
  bundles of HTML in your site content that you'd like copied as-is, you can
  mark them as 'asset' in [`.staticsite` directory metadata](doc/contents.md).

### Link stability

* `tag/archive.html` is now `tag/archive`
* Static assets loaded by themes are now moved into a `static/` directory in
  the rendered website. `url_for` generates the right links for them, but if
  one had hardcoded links to them in the site, or external sites linked to the
  site static assets, those links may end up broken

### Templates

* Where you used `page.pages`, now use `page.meta.pages`
* Where you used `contents` for rendered page contents, now you use
  `page.contents`
* Data pages now honor the `page.meta.template` metadata, and are rendered
  directly by that template, with using one template for contents and one for
  the page layout. If you use data pages, change your `data-$TYPE.html`
  templates to extend `page.html` and render into the `page_content` block.

# New in version 1.1

* Documented and consolidated the Features feature
* Reuse existing static content in destination directory to speed up rendering
* Allow invoking feature-specific code from the command line
  (`ssite site --cmd …`)

# New in version 1.0

* Refactored codebase to introduce the concept of pluggable Features. Most
  staticsite features are now implemented as pluggable features, and new
  features can be provided with python modules placed in the
  `$THEMEDIR/features/` directory
* Implemented data pages, as yaml, toml, or json, that provide pure datasets.
  `data-$type.html` jinja2 templates can be used to render their contents.
* Speed up site rebuilds by caching intermediate markdown contents

**Upgrade notes**:

 * To prevent the creation of a cache directory in your `PROJECT_ROOT`, set the
   new `CACHE_REBUILDS` setting to `False`.

# New in version 0.6

* Allow filtering by taxonomies in `site_pages()`
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

* Allow pointing to .py configuration instead of project on command line.
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

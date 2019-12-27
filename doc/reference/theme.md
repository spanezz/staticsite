# theme: controlling the appearance of the site

Inside a theme directory there are the [Jinja2](http://jinja.pocoo.org/)
templates that control how pages are rendered, and static assets for the theme.

The theme contents are independent from the contents of the site, and it should
be possible to swap one theme for another at any point.


## Theme configuration

If a `config` file is found in the theme directory, it is parsed as `yaml`,
`json`, or `toml` data, and used as theme configuration.

Valid theme configuration entries currently are:

* `system_assets`: list of names of directories under `/usr/share/javascript`
  to be added as static assets to the site
* `extends`: name or list of names of themes that this theme depends on. See
  **Theme inheritance** below for details.

## Theme templates

These templates are used by default by `staticsite`:

* `dir.html` is used to render directory indices.
* `page.html` is used to render Markdown pages.
* `redirect.html` is used to render placeholder pages that redirect to the new
  location where a page can now be found.

These templates are expected to be present by the Jinja2 templates
inside `content`:

* `base.html` is used for the common parts of all pages.
* `syndication.xml` contains jinja2 macros used to generate RSS2 and Atom
  feeds.
* `lib/blog.html` macro library with functions to render blogs and category pages.

These templates are used by [taxonomy pages](taxonomies.md):

* `taxonomy/taxonomy.html` is used for the index of all categories in the taxonomy.
* `taxonomy/category.html` is used to generate the page for each category.
* `taxonomy/archive.html` is used to generate the archive page for each category.

See [the template documentation](templates.md) for a reference on writing
templates.

## Static assets

The contents of a `static` directory in the theme directory are added as static
assets to the site.

Other static assets are loaded from `/usr/share/javascript` as listed in the
`SYSTEM_ASSETS` [setting](settings.md) or in the `system_assets` theme
configuration.


## Theme inheritance

A theme can list dependencies on other themes via the `extends` configuration
entry.

At theme load time, the configuration of all the themes in the dependency chain
is read, and the whole tree of dependencies is flattened into a list, with the
dependencies always preceding the themes they depend on.

### Features

Features for the site are loaded from all the theme feature directories, if
present.

### Templates

Templates are looked up in the site contents, then in the main theme, then
down the theme dependency chains.

### Assets

Assets are loaded from all the `system_assets` directories configured in all
the templates in the chain, removing duplicates.

Then assets are loaded from all the `static/` directories in all the templates
in the dependency chain, from the bottom-most dependency upwards.

[Back to reference index](README.md)

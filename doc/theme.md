# theme: controlling the appearance of the site

Inside `theme` there are the [Jinja2](http://jinja.pocoo.org/) templates that
control how pages are rendered.

The theme contents are independent from the contents of the site, and it should
be possible to swap one theme for another at any point.

## Theme configuration

If a `config` file is found in the theme directory, it is parsed as `yaml`,
`json`, or `toml` data, and used as theme configuration.

Valid theme configuration entries currently are:

* `system_assets`: list of names of directories under `/usr/share/javascript`
  to be added as static assets to the site


## Theme templates

These templates are directly used by `staticsite`:

* `dir.html` is used to render directory indices.
* `page.html` is used to render Markdown pages.
* `redirect.html` is used to render placeholder pages that redirect to the new
  location where a page can now be found.

These templates are expected to be present by the Jinja2 templates
inside `content`:

* `base.html` is used for the common parts of all pages.
* `inline_page.html` is used for rendering other pages inline, for example in
  the front page of a blog, or in the index page of a tag.
* `syndication.xml` contains macro used to generate RSS2 and Atom feeds.

For each [taxonomy](taxonomies.md), a number of templates are also expected. In
the case of a taxonomy called `tags` with `item_name` `tag`:

* `tags.html` is used for the main page of the taxonomy.
* `tag.html` is used to generate each tag page.
* `tag-archive.html` is used to generate an archive page for each tag.
* `tag.atom` is used for the Atom feed for each tag.
* `tag.rss` is used for the RSS2 feed for each tag.


## Static assets

The contents of a `static` directory in the theme directory are added as static
assets to the site.

Other static assets are loaded from `/usr/share/javascript` as listed in the
`SYSTEM_ASSETS` [setting](settings.md) or in the `system_assets` theme
configuration.

[Back to README](../README.md)

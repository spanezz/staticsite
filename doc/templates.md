# Jinja2 templates in staticsite

## Jinja2 files in `content`

Any files called `<name>.j2.<ext>` will be rendered with
[Jinja2](http://jinja.pocoo.org/) to generate `<name>.<ext>`.

This can be used to generate complex index pages, blog front pages, RSS2 and
Atom feeds, and anything else Jinja2 is able to generate.


## Jinja2 environment

The `theme` directory is in the Jinja2 search path, and you can `{% import %}`
or `{% include %}` anything from it.

Any setting defined in `settings.py` is also available to Jinja2, so you can do
for example:

```jinja2
<a class="navbar-brand" href="{{SITE_ROOT}}">{{SITE_NAME}}</a>
```

Extra functions provided to Jinja2 templates:

 * `url_for("path/page")`: returns the URL that links to the page or asset with
   the given path. The path is resolved relative to the current page, and if
   not found, relative to the parent page, and so on until the top.
 * `url_for(page)`: returns the URL that links to the given page.
 * `site_pages(path=None, limit=None, sort="-date", **kw)`: return a list of
   pages defined in the site that match the given arguments. See
   [Selecting pages](page_filter.md) for details.
 * `now`: the current date and time.
 * `next_month`: midnight of the first day of next month. Useful in archetypes
   front matter to collect content into monthly pages.
 * `taxonomies()`: a list of all known taxonomies.
 * `regex()`: alias to `re.compile`, which can be used to explicitly interpret
   a `site_pages` argument as a regular expression

Extra filters provided to Jinja2 templates:

 * `|datetime_format(format=None)` formats a datetime. Formats
   supported: "rss2", "rfc822", "atom", "rfc3339", "w3ctdf",
   "[iso8601](https://xkcd.com/1179/)" (default). If the format
   starts with `%` it is considered a [strftime](http://strftime.org/)
   format string.
 * `basename` returns the file name part of a pathname.
 * `markdown` renders the string using [markdown](markdown.md).

Each feature can make more filters and functions available to Jinja2 templates:
see the documentation for each feature for what is made available.

When a `page` is passed to Jinja2, it has at least a `meta` member, pointing to
the [metadata for the page](metadata.md).

Depending on the feature that created the page, a page can have extra members,
documented in each feature documentation.


[Back to README](../README.md)

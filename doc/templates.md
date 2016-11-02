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
 * `site_pages(path=None, limit=None, sort="-date")`: return a list of pages
   defined in the site that match the given arguments. `path` is a file glob
   (like `"blog/*"`) that matches the page file name. `limit` is the maximum
   number of pages to return. `sort` is the `page.meta` field to use to sort
   the pages. Prefix `sort` with a dash (`-`) for reverse sorting.
            now=self.generation_time,
 * `now`: the current date and time.
 * `next_month`: midnight of the first day of next month. Useful in archetypes
   front matter to collect content into monthly pages.
 * `taxonomies()`: a list of all known taxonomies.

Extra filters provided to Jinja2 templates:

 * `|datetime_format(format=None)` formats a datetime. Formats
   supported: "rss2", "rfc822", "atom", "rfc3339", "w3ctdf",
   "[iso8601](https://xkcd.com/1179/)" (default).
 * `basename` returns the file name part of a pathname.
 * `markdown` renders the string using [markdown](markdown.md).

Each taxonomy defines extra `url_for_*` functions. For example, given a *tags*
taxonomy with *tag* as singular name:

 * `url_for_tags()`: links to the taxonomy index.
 * `url_for_tag(tag)`: links to the tag index.
 * `url_for_tag_archive(tag)`: links to the tag archive page.
 * `url_for_tag_rss(tag)`: links to the RSS2 feed for the tag.
 * `url_for_tag_atom(tag)`: links to the Atom feed for the tag.

When a `page` is passed to Jinja2, it has these members:

 * `page.meta`: all the metadata for the page, like `page.meta.title`,
   `page.meta.date`, `page.meta.tags` and anything else you have in the front
   matter.

When a `tag` (or other taxonomy element) is passed to Jinja2, it has these
members:

 * `tag.name`: the tag name
 * `tag.slug`: the [slug](https://en.wikipedia.org/wiki/Semantic_URL#Slug) for
   the tag
 * `tag.pages`: unordered list of pages with this tag

When a taxonomy is passed to Jinja2, it has these members:

 * `taxonomy.meta`: all the metadata, just like a page. You can also pass a
   taxonomy to `url_for`, to link to its main page.
 * `taxonomy.items`: dict mapping taxonomy element names to taxonomy elements.


[Back to README](../README.md)

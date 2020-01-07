# Jinja2 templates in staticsite

Staticsite uses [jinja2](http://jinja.pocoo.org/) as a template engine.


## Jinja2 environment

The [site contents](contents.md) and the [`theme` directory](theme.md) are both
in the Jinja2 search path, and you can `{% import %}` or `{% include %}`
anything from them.

This is a reference to the basic contents of template contexts in staticsite.

Each [feature](features.md) can provide more filters and functions to Jinja2
templates: see the documentation of the various features for details.


### Site and page

* `site` is available as the current [site object](site.md)
* `page` is available as the current page object. If present, it has at least a
  `meta` member, pointing to the [metadata for the page](metadata.md).
  Feature-specific pages can have extra membres, which are documented in each
  feature documentation. You can use `ssite dump_meta` to see all the content that pages make available to templates.

### Site settings

Any setting defined in `settings.py` is also available to Jinja2, so you can do
for example:

```jinja2
<small>Built with staticsite and theme {{THEME|basename}}</small>
```

### Functions

* `url_for("path/page")`: returns the URL that links to the page or asset with
  the given path.
  The path is resolved relative to the current page, or to the root of the site
  or content directory if it is an absolute path.
* `url_for(page)`: returns the URL that links to the given page.
* `page_for("path/page")`: returns the page with the given path.
  The path is resolved relative to the current page, or to the root of the site
  or content directory if it is an absolute path.
* `page_for(page)`: returns the page itself.
* `site_pages(path=None, limit=None, sort=None, root=None, **kw)`: return a
  list of pages defined in the site that match the given arguments. See
  [Selecting pages](page-filter.md) for details.
  This is an alias to `page.find_pages()`
* `now`: the current date and time, alias to `site.generation_time`.
* `next_month`: midnight of the first day of next month. Useful in archetypes
  front matter to collect content into monthly pages.
* `taxonomies()`: a list of all known taxonomies.
* `regex()`: alias to `re.compile`, which can be used to explicitly interpret
  a `site_pages` argument as a regular expression
* `img_for(Union[str, Page], type=None, **attrs)`: create an `<img>` tag for
  the given image or path to an image, with the `alt`, `src`, `srcset`,
  `width`, `height` tags filled as needed. Use `type` to choose one of the
  [configured scaled versions](images.md) of the image. Do not use `type` to
  generate a `srcset` attribute that allows the browser to choose
  automatically. You can provide extra element attributes to the `<img>` tag as
  keyword arguments to the function.

### Filters

 * `|datetime_format(format=None)` formats a datetime. Formats
   supported: "rss2", "rfc822", "atom", "rfc3339", "w3ctdf",
   "[iso8601](https://xkcd.com/1179/)" (default). If the format
   starts with `%` it is considered a [strftime](http://strftime.org/)
   format string.
 * `|basename` returns the file name part of a pathname.
 * `|markdown` renders the string using [markdown](markdown.md).
 * `|arrange(sort, limit=None)` sorts a list of pages, and returns the first
   `limit` ones. If `limit` is not specified, returns the whole sorted list of
   pages. `sort` takes the same values as in [page filters](page-filter.md).


### Template loading

Referring to a template by path, looks it up in theme directories. If a
template is not found in a theme, it is looked up in the themes it extends.

Prefix a template name with `content:` to look it up in the site content
directory insted. This way you could have content pages that extend other
content pages, or a local base template in the content directory that extends
the one from the theme.

[Back to reference index](README.md)

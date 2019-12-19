# Selecting site pages

Functions like `site_pages` in [templates](templages.md) or `filter`/`add_to`
in [syndication](syndication.md) allow selecting pages from the site.

These parameters can be used to choose pages:

 * `path`: glob or regular expression that matches the file name in the site
   contents directory. It is used as a file glob (like `"blog/*"`), unless it
   starts with `^` or ends with `$`: then it is considered a regular
   expression.

 * `sort`: order the results according to the given metadata item. Prepend a
   dash (`-`) for reverse sorting. Use `url` or `-url` to sort by the url of
   the page in the website.
   
 * `limit` is the maximum number of pages to return.
   
Any taxonomy defined in the site becomes a possible parameter for filtering,
and is a list of categories of that taxonomy: pages must have all those
categories to be selected.

Note that in many cases, you may want to omit `sort` and `limit` from
`site_pages` and page front matter, and decide sorting and limit in templates
with [the `arrange()` filter](templates.md).

## Example:

List blog articles about Debian in a template:

```jinja2
{% for page in site_pages(path="blog/*", tags=["debian"], sort="-date") %}
<li>{{url_for(page)}}</li>
{% endfor %}
```


[Back to reference index](reference.md)

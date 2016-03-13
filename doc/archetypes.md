# Archetypes

## Creating new pages

```bash
$ ./ssite new example
Please enter the page title: An example new page
(editor opens)
```

`staticsite` uses [Hugo-style archetypes](https://gohugo.io/content/archetypes/).

By default, `archetypes/default.md` is used as a template for new pages, and
you can use the `-a` or `--archetype` option to pick another one.

The archetype is processed via the same Jinja2 logic as the rest of the site,
plus the `title` and `slug` variables for the article. The `path` value in the
front matter is used to decide where to write the file, and is removed before
writing the page.

The editor and editor command line can also be configured, see
`global_settings.py` for details and examples.

[Back to README](../README.md)

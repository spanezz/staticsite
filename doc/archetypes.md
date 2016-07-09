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

# Archetypes tips

## Monthly collection of links

`example/archetypes/links.md` is an example of how to use archetypes to publish
a monthly collection of links:

```jinja2
+++
path = "blog/{{next_month.strftime("%Y")}}/links-{{next_month.strftime("%m")}}.md"
date = "{{next_month|datetime_format()}}"
tags = ["ssite new -a linkslinks"]
+++
# Links for {{next_month.strftime("%B %Y")}}
…
```

Use `ssite new -a links` to add a link to the collection.

The path and title of the page will be generated based on next month only, and
the page will not be published while links are being collected. When the next
month comes, the page will be published and `ssite new -a links` will start a
new page.


[Back to README](../README.md)

# Common page metadata

This is a list of metadata elements that are currently used by staticsite.

Features can make use of other metadata. See for example
[syndication](syndication.md), and [taxonomies](taxonomies.md).

You can use `ssite dump_meta` to see all the content and metadata that pages
make available to templates via the `page` variable.


### `template`

Template used to render the page. Defaults to `page.html`,

Although specific pages of some features can default to other template names.
Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).

### `date`

A python datetime object, timezone aware. If the date is in the future when
`ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
--draft` to also consider draft pages.

### `title`

The page title. If omitted, the first title found in the page is used. If the
page has no title, the file name for the page will be used.

### `template_title`

If set instead of title, it is a jinja2 template used to generate the title.
The template context will have `page` available, with the current page. The
result of the template will not be further escaped, so you can use HTML markup
in it.

### `description`

The page description. If omitted, the page will have no description.

### `template_description`

If set instead of description, it is a jinja2 template used to generate the
description. The template context will have `page` available, with the current
page. The result of the template will not be further escaped, so you can use
HTML markup in it.

### *`any_taxonomy_name`*

If you define a taxonomy, its name will be used in the metadata as the list of
categories for the page.

For example, if you define a `tags` taxonomy, you can set `tags` to a list of
tags for the page.

### `aliases`

Relative paths in the destination directory where the page should also show up.
[Like in Hugo](https://gohugo.io/extras/aliases/), this can be used to maintain
existing links when moving a page to a different location.

### `asset`

If set to True in [`.staticsite` directory metadata](contents.md), the file is
loaded as a static asset, regardless of whether a feature would load it.

### `indexed`

If true, the page appears in [directory indices](dir.md) and in
[page filter results](page_filter.md). It defaults to true for
[Markdown](markdown.md), [reStructuredText](rst.rst), and [data](data.md)
pages.


[Back to reference index](reference.md)

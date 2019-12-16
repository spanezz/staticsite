# Common page metadata

This is a list of metadata elements that are currently used by staticsite.

Features can make use of other metadata. See for example
[syndication](syndication.md), and [series](series.md).

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

### `series`

Name identifying a [series of articles](series.md) that this page is a part of.

### `series_title`, `series_prev`, `series_next`, `series_first`, `series_last`, `series_index`, `series_length`
   
See [series of articles](series.md).

[Back to reference index](reference.md)

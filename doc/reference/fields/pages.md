# pages: The `pages` metadata can use to select a set of pages shown by the current
page. Although default `page.html` template will not do anything with them,
other page templates, like `blog.html`, use this to select the pages to show.

The `pages` feature allows defining a [page filter](page-filter.md) in the
`pages` metadata element, which will be replaced with a list of matching pages.

To select pages, the `pages` metadata is set to a dictionary that select pages
in the site, with the `path`, and taxonomy names arguments similar to the
`site_pages` function in [templates](templates.md).

See [Selecting pages](page-filter.md) for details.

[Back to reference index](../README.md)

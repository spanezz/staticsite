# asset: A static asset, copied as is

## Fields

* [asset](../fields/asset.md): If set to True for a file (for example, by a `file:` pattern in a directory
index), the file is loaded as a static asset, regardless of whether a feature
would load it.
* [author](../fields/author.md): A string with the name of the author for this page.
* [copyright](../fields/copyright.md): Copyright notice for the page. If missing, it's generated using
`template_copyright`.
* [date](../fields/date.md): Publication date for the page.
* [description](../fields/description.md): The page description. If omitted, the page will have no description.
* [draft](../fields/draft.md): If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.
* [indexed](../fields/indexed.md): If true, the page appears in [directory indices](dir.md) and in
[page filter results](page_filter.md).
* [pages](../fields/pages.md): The `pages` metadata can use to select a set of pages shown by the current
page. Although default `page.html` template will not do anything with them,
other page templates, like `blog.html`, use this to select the pages to show.
* [related](../fields/related.md): Readonly mapping of pages related to this page, indexed by name.
* [site_name](../fields/site_name.md): Name of the site. If missing, it defaults to the title of the toplevel index
page. If missing, it defaults to the name of the content directory.
* [site_url](../fields/site_url.md): Base URL for the site, used to generate an absolute URL to the page.
* [template_copyright](../fields/template_copyright.md): jinja2 template to use to generate `copyright` when it is not explicitly set.
* [template_description](../fields/template_description.md): jinja2 template to use to generate `description` when it is not
explicitly set.
* [template_title](../fields/template_title.md): jinja2 template to use to generate `title` when it is not explicitly set.
* [title](../fields/title.md): Page title.

## Documentation

A static asset, copied as is

[Back to reference index](../README.md)

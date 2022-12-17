# scaledimage: Scaled version of an image

## Fields

* [aliases](../fields/aliases.md): Relative paths in the destination directory where the page should also show up.
[Like in Hugo](https://gohugo.io/extras/aliases/), this can be used to maintain
existing links when moving a page to a different location.
* [asset](../fields/asset.md): If set to True for a file (for example, by a `file:` pattern in a directory
index), the file is loaded as a static asset, regardless of whether a feature
would load it.
* [author](../fields/author.md): A string with the name of the author for this page.
* [copyright](../fields/copyright.md): Copyright notice for the page. If missing, it's generated using
`template_copyright`.
* [created_from](../fields/created_from.md): Page that generated this page.
* [data_type](../fields/data_type.md): Type of data for this file.
* [date](../fields/date.md): Publication date for the page.
* [description](../fields/description.md): The page description. If omitted, the page will have no description.
* [height](../fields/height.md): Image height
* [image](../fields/image.md): Image used for this post.
* [indexed](../fields/indexed.md): If true, the page appears in [directory indices](dir.md) and in
[page filter results](page_filter.md).
* [links](../fields/links.md): Extra metadata for external links.
* [nav](../fields/nav.md): List of page paths, relative to the page defining the nav element, that
are used for the navbar.
* [nav_title](../fields/nav_title.md): Title to use when this page is linked in a navbar.
* [pages](../fields/pages.md): The `pages` metadata can use to select a set of pages shown by the current
page. Although default `page.html` template will not do anything with them,
other page templates, like `blog.html`, use this to select the pages to show.
* [related](../fields/related.md): Dict of pages related to this page.
* [series](../fields/series.md): List of categories for the `series` taxonomy.
* [series_title](../fields/series_title.md): Series title from this page onwards.
* [site_name](../fields/site_name.md): Name of the site. If missing, it defaults to the title of the toplevel index
page. If missing, it defaults to the name of the content directory.
* [site_url](../fields/site_url.md): Base URL for the site, used to generate an absolute URL to the page.
* [syndicated](../fields/syndicated.md): Set to true if the page can be included in a syndication, else to false.
* [syndication](../fields/syndication.md): Defines syndication for the contents of this page.
* [syndication_date](../fields/syndication_date.md): Syndication date for this page.
* [tags](../fields/tags.md): List of categories for the `tags` taxonomy.
* [template](../fields/template.md): Template used to render the page. Defaults to `page.html`, although specific
pages of some features can default to other template names.
* [template_copyright](../fields/template_copyright.md): jinja2 template to use to generate `copyright` when it is not explicitly set.
* [template_description](../fields/template_description.md): jinja2 template to use to generate `description` when it is not
explicitly set.
* [template_title](../fields/template_title.md): jinja2 template to use to generate `title` when it is not explicitly set.
* [title](../fields/title.md): Page title.
* [width](../fields/width.md): Image width

## Documentation

Scaled version of an image

[Back to reference index](../README.md)

# jinja2: Jinja2 pages

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
* [data_type](../fields/data_type.md): Type of data for this file.
* [date](../fields/date.md): Publication date for the page.
* [description](../fields/description.md): The page description. If omitted, the page will have no description.
* [draft](../fields/draft.md): If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.
* [height](../fields/height.md): Image height
* [image](../fields/image.md): Image used for this post.
* [indexed](../fields/indexed.md): If true, the page appears in [directory indices](dir.md) and in
[page filter results](page_filter.md).
* [links](../fields/links.md): Extra metadata for external links.
* [nav](../fields/nav.md): List of page paths, relative to the page defining the nav element, that
are used for the navbar.
* [nav_title](../fields/nav_title.md): Title to use when this page is linked in a navbar.
* [old_footprint](../fields/old_footprint.md): Cached footprint from the previous run, or None
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

You can put [jinja2 templates](templates.md) in your site contents, and they
will be rendered as site pages.

This can be used to generate complex index pages, blog front pages, and
anything else [Jinja2](http://jinja.pocoo.org/) is able to generate.

You can set `JINJA2_PAGES` in the [site settings](settings.md) to a list of
patterns (globs or regexps as in [page filters](page-filter.md)) matching file
names to consider jinja2 templates by default. It defaults to
`["*.html", "*.j2.*"]`.

Any file with `.j2.` in their file name will be rendered as a template,
stripping `.j2.` in the destination file name.

For example, `dir/robots.j2.txt` will become `dir/robots.txt` when the site is
built.

## Front matter

If a page defines a jinja2 block called `front_matter`, the block is rendered
and parsed as front matter.

**Note**: [jinja2 renders all contents it finds before
`{% extends %}`](https://jinja.palletsprojects.com/en/2.10.x/templates/#child-template).
To prevent your front matter from ending up in the rendered HTML, place the
`front_matter` block after the `{% extends %}` directive, or manage your front
matter from [`.staticfile` directory metadata](content.md).

If you want to use `template_*` entries, you can wrap the front matter around
`{% raw %}` to prevent jinja2 from rendering their contents as part of the rest
of the template.

[Back to reference index](../README.md)

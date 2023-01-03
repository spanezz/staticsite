# rst: RestructuredText files

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
* [front_matter](../fields/front_matter.md): Front matter as parsed by the source file
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
* [related](../fields/related.md): Readonly mapping of pages related to this page, indexed by name.
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

## Documentation

RestructuredText files have a `.rst` extension and their metadata are taken
from docinfo information.

`staticsite` will postprocess the RestructuredText doctree to adjust internal
links to guarantee that they point where they should.


## Linking to other pages

Pages can link to other pages via any of the normal reSt links.

Links that start with a `/` will be rooted at the top of the site contents.

Relative links are resolved relative to the location of the current page first,
and failing that relative to its parent directory, and so on until the root of
the site.

For example, if you have `blog/2016/page.rst` that contains a link to
`images/photo.jpg`, the link will point to the first of this
options that will be found:

1. `blog/2016/images/photo.jpg`
2. `blog/images/photo.jpg`
3. `images/photo.jpg`

This allows organising pages pointing to other pages or assets without needing
to worry about where they are located in the site.

You can link to other Markdown or RestructuredText pages with the `.md` or
`.rst` extension ([like GitHub does](https://help.github.com/articles/relative-links-in-readmes/))
or without, as if you were editing a wiki.


Page metadata
-------------

As in [Sphinx](http://www.sphinx-doc.org/en/stable/markup/misc.html#file-wide-metadata),
a field list near the top of the file is parsed as front matter and removed
from the generated files.

All [bibliographic fields](http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#bibliographic-fields)
known to docutils are parsed according to their respective type.

All fields whose name matches a taxonomy defined in `TAXONOMY_NAMES`
[settings](../settings.md)_ are parsed as yaml, and expected to be a list of
strings, with the set of values (e.g. tags) of the given taxonomy for the
current page.

See [page metadata](../metadata.md) for a list of commonly used metadata.


## Rendering reStructuredText pages
--------------------------------

Besides the usual `meta`, reStructuredText pages have also these attributes:

* `page.contents`: the reSt contents rendered as HTML. You may want to use
  it with the [`|safe` filter](https://jinja.palletsprojects.com/en/2.10.x/templates/#safe)
  to prevent double escaping

[Back to reference index](../README.md)

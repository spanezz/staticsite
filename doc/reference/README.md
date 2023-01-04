# Reference documentation

## Core structure

* [The Site object](site.md)
* [Site settings](settings.md)
* [Source contents](contents.md)
* [Themes](theme.md)
* [Selecting site pages](page-filter.md)
* [Archetypes reference](archetypes.md)
* [Site-specific features](feature.md)
* [Front Matter](front-matter.md)

## Features

* [aliases](features/aliases.md): Build redirection pages for page aliases.
* [data](features/data.md): Handle datasets in content directories.
* [dirindex](features/dirindex.md): Build redirection pages for page aliases.
* [images](features/images.md): Handle images in content directory.
* [jinja2](features/jinja2.md): Render jinja2 templates from the contents directory.
* [links](features/links.md): Collect links and link metadata from page metadata.
* [md](features/md.md): Render ``.md`` markdown pages, with front matter.
* [nav](features/nav.md): Expand a 'pages' metadata containing a page filter into a list of pages.
* [rst](features/rst.md): Render ``.rst`` reStructuredText pages, with front matter.
* [syndication](features/syndication.md): Build syndication feeds for groups of pages.
* [taxonomy](features/taxonomy.md): Tag pages using one or more taxonomies.

## Page types

* [alias](pages/alias.md): Page rendering a redirect to another page
* [archive](pages/archive.md): An archive page is automatically created for each syndication.
* [asset](pages/asset.md): A static asset, copied as is
* [atom](pages/atom.md): An Atom syndication page
* [category](pages/category.md): Index page showing all the pages tagged with a given taxonomy item
* [data](pages/data.md): Data files
* [dir](pages/dir.md): Page with a directory index.
* [image](pages/image.md): An image as found in the source directory
* [jinja2](pages/jinja2.md): Jinja2 pages
* [links](pages/links.md): Page with a link collection posted as metadata only.
* [links_index](pages/links_index.md): Root page for the browseable archive of annotated external links in the
site
* [markdown](pages/markdown.md): Markdown sources
* [rss](pages/rss.md): A RSS syndication page
* [rst](pages/rst.md): RestructuredText files
* [scaledimage](pages/scaledimage.md): Scaled version of an image
* [taxonomy](pages/taxonomy.md): Root page for one taxonomy defined in the site

## Page fields

* [aliases](fields/aliases.md): Relative paths in the destination directory where the page should also show up.
[Like in Hugo](https://gohugo.io/extras/aliases/), this can be used to maintain
existing links when moving a page to a different location.
* [asset](fields/asset.md): If set to True for a file (for example, by a `file:` pattern in a directory
index), the file is loaded as a static asset, regardless of whether a feature
would load it.
* [author](fields/author.md): A string with the name of the author for this page.
* [copyright](fields/copyright.md): Copyright notice for the page. If missing, it's generated using
`template_copyright`.
* [created_from](fields/created_from.md): Page that generated this page.
* [data_type](fields/data_type.md): Type of data for this file.
* [date](fields/date.md): Publication date for the page.
* [description](fields/description.md): The page description. If omitted, the page will have no description.
* [draft](fields/draft.md): If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.
* [front_matter](fields/front_matter.md): Front matter as parsed by the source file
* [height](fields/height.md): Image height
* [image](fields/image.md): Image used for this post.
* [image_orientation](fields/image_orientation.md): Image orientation
* [index](fields/index.md): Page that defined the syndication for this feed
* [indexed](fields/indexed.md): If true, the page appears in [directory indices](dir.md) and in
[page filter results](page_filter.md).
* [lat](fields/lat.md): Image latitude
* [links](fields/links.md): Extra metadata for external links.
* [lon](fields/lon.md): Image longitude
* [name](fields/name.md): Name of the category shown in this page
* [nav](fields/nav.md): List of page paths, relative to the page defining the nav element, that
are used for the navbar.
* [nav_title](fields/nav_title.md): Title to use when this page is linked in a navbar.
* [page](fields/page.md): Page this alias redirects to
* [pages](fields/pages.md): The `pages` metadata can use to select a set of pages shown by the current
page. Although default `page.html` template will not do anything with them,
other page templates, like `blog.html`, use this to select the pages to show.
* [parent](fields/parent.md): Page one level above in the site hierarchy
* [related](fields/related.md): Readonly mapping of pages related to this page, indexed by name.
* [series](fields/series.md): List of categories for the `series` taxonomy.
* [series_title](fields/series_title.md): Series title from this page onwards.
* [site_name](fields/site_name.md): Name of the site. If missing, it defaults to the title of the toplevel index
page. If missing, it defaults to the name of the content directory.
* [site_url](fields/site_url.md): Base URL for the site, used to generate an absolute URL to the page.
* [syndicated](fields/syndicated.md): Set to true if the page can be included in a syndication, else to false.
* [syndication](fields/syndication.md): Defines syndication for the contents of this page.
* [syndication_date](fields/syndication_date.md): Syndication date for this page.
* [tags](fields/tags.md): List of categories for the `tags` taxonomy.
* [taxonomy](fields/taxonomy.md): Page that defined this taxonomy
* [template](fields/template.md): Template used to render the page. Defaults to `page.html`, although specific
pages of some features can default to other template names.
* [template_copyright](fields/template_copyright.md): jinja2 template to use to generate `copyright` when it is not explicitly set.
* [template_description](fields/template_description.md): jinja2 template to use to generate `description` when it is not
explicitly set.
* [template_title](fields/template_title.md): jinja2 template to use to generate `title` when it is not explicitly set.
* [title](fields/title.md): Page title.
* [width](fields/width.md): Image width

[Back to README](../../README.md)

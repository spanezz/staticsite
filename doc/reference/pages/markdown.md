# markdown: Markdown sources

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

Markdown files have a `.md` extension and are prefixed by
[front matter metadata](../front-matter.md).

The flavour of markdown is what's supported by
[python-markdown](http://pythonhosted.org/Markdown/) with the
[Extra](http://pythonhosted.org/Markdown/extensions/extra.html),
[CodeHilite](http://pythonhosted.org/Markdown/extensions/code_hilite.html)
and [Fenced Code Blocks](http://pythonhosted.org/Markdown/extensions/fenced_code_blocks.html)
extensions, and is quite close to
[GitHub Flavored Markdown](https://github.github.com/gfm/) or
[GitLab Markdown](https://docs.gitlab.com/ee/user/markdown.html).

`staticsite` adds an extra internal plugin to Python-Markdown to postprocess
the page contents to adjust internal links to guarantee that they point where
they should.

Adding a horizontal rule *using underscores* (3 or more underscores), creates a
page fold. When rendering the page inline, such as in a blog index page, or in
RSS/Atom syndication, the content from the horizontal rule onwards will not be
shown.

If you want to add a horizontal rule without introducing a page fold, use a
sequence of three or more asterisks (`***`) or dashes (`---`) instead.


## Linking to other pages

Pages can link to other pages via normal Markdown links (`[text](link)`).

Links that start with a `/` will be rooted at the top of the site contents.

Relative links are resolved relative to the location of the current page first,
and failing that relative to its parent directory, and so on until the root of
the site.

For example, if you have `blog/2016/page.md` that contains a link like
`![a photo](images/photo.jpg)`, the link will point to the first of this
options that will be found:

1. `blog/2016/images/photo.jpg`
2. `blog/images/photo.jpg`
3. `images/photo.jpg`

This allows one to organise pages pointing to other pages or assets without needing
to worry about where they are located in the site.

You can link to other Markdown pages with the `.md` extension
([like GitHub does](https://help.github.com/articles/relative-links-in-readmes/))
or without, as if you were editing a wiki.

## Page metadata

The front matter of the post can be written in
[TOML](https://github.com/toml-lang/toml),
[YAML](https://en.wikipedia.org/wiki/YAML) or
[JSON](https://en.wikipedia.org/wiki/JSON), just like in
[Hugo](https://gohugo.io/content/front-matter/).

Use `---` delimiters to mark YAML front matter. Use `+++` delimiters to mark
TOML front matter. Use `{`…`}` delimiters to mark JSON front matter.

You can also usea [triple-backticks code blocks](https://python-markdown.github.io/extensions/fenced_code_blocks/)
first thing in the file to mark front matter, optionally specifying `yaml`,
`toml`, or `json` as the format (yaml is used as a default):

~~~~{.markdown}
```yaml
date: 2020-01-02 12:00
```
# My page
~~~~

If you want to start your markdown content with a code block, add an empty line
at the top: front matter detection only happens on the first line of the file.

See [page metadata](../metadata.md) for a list of commonly used metadata.


## Extra settings

Markdown rendering makes use of these settings:

### `MARKDOWN_EXTENSIONS`

Extensions used by python-markdown. Defaults to:

```py
MARKDOWN_EXTENSIONS = [
    "markdown.extensions.extra",
    "markdown.extensions.codehilite",
    "markdown.extensions.fenced_code",
]
```

### `MARKDOWN_EXTENSION_CONFIGS`

Configuration for markdown extensions. Defaults to:

```py
MARKDOWN_EXTENSION_CONFIGS = {
    'markdown.extensions.extra': {
        'markdown.extensions.footnotes': {
            # See https://github.com/spanezz/staticsite/issues/13
            'UNIQUE_IDS': True,
        },
    },
}
```

## Rendering markdown pages

Besides the usual `meta`, markdown pages have also these attributes:

* `page.contents`: the Markdown contents rendered as HTML. You may want to use
  it with the [`|safe` filter](https://jinja.palletsprojects.com/en/2.10.x/templates/#safe)
  to prevent double escaping

[Back to reference index](../README.md)

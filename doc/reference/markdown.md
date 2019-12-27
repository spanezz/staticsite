# Markdown pages

Markdown files have a `.md` extension and are prefixed by
[front matter metadata](front-matter.md).

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

See [page metadata](metadata.md) for a list of commonly used metadata.


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

[Back to reference index](README.md)

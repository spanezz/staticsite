# Markdown files

Markdown files have a `.md` extension and are prefixed by a [Hugo-style front
matter](https://gohugo.io/content/front-matter/).

The flavour of markdown is what's supported by
[python-markdown](http://pythonhosted.org/Markdown/) with the
[Extra](http://pythonhosted.org/Markdown/extensions/extra.html),
[CodeHilite](http://pythonhosted.org/Markdown/extensions/code_hilite.html)
and [Fenced Code Blocks](http://pythonhosted.org/Markdown/extensions/fenced_code_blocks.html)
extensions.

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

This allows to organise pages pointing to other pages or assets without needing
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

This is a list of all metadata elements that are currently in use:

 - `date`: a python datetime object, timezone aware. If the date is in the
   future when `ssite` runs, the page will be consider a draft and will be
   ignored. Use `ssite --draft` to also consider draft pages.
 - `title`: the page title. If omitted, the first `#` title is used.
 - `tags`: list of tags for the page. If you define a new taxonomy, its name in
   the metadata will be used in the same way.
 - `aliases`: relative paths in the destination directory where the page should
   also show up. [Like in Hugo](https://gohugo.io/extras/aliases/), this can be
   used to maintain existing links when moving a page to a different location.

[Back to README](../README.md)

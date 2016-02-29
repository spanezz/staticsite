+++
# This is the front matter of the post. It contains metadata for the post, but
# it is not part of the Markdown contents.

# Title used in HTML <title>. If omitted, using the first toplevel heading
# (a single #) in the file.
# title = "Example blog post"

# Date of the post. You can use anything understood by dateutil.parser
# (http://dateutil.readthedocs.org/en/latest/parser.html)
date = "2016-02-29 19:00:00+01:00"

# List of tags for this page
tags = [ "example" ]

# You can similarly use any taxonomy you have defined for the site
# categories = [ "boilerplate" ]
# series = [ "Creating a new blog" ]

# Markdown begins after the end marker of the front matter:
+++

# Example blog post

This is an example blog post, in
[Markdown](https://daringfireball.net/projects/markdown/syntax).

The front matter of the post can be written in
[TOML](https://github.com/toml-lang/toml),
[YAML](https://en.wikipedia.org/wiki/YAML) or
[JSON](https://en.wikipedia.org/wiki/JSON), just like in
[Hugo](https://gohugo.io/content/front-matter/).

Syntax highlighting works:

```py
import this
```

Also, inline images work:

![An example image](example.png)

(image from [wikimedia commons](https://commons.wikimedia.org/wiki/File:Example_image.png)).

The flavour of markdown is what's supported by
[python-markdown](http://pythonhosted.org/Markdown/) with the 
[Extra](http://pythonhosted.org/Markdown/extensions/extra.html),
[CodeHilite](http://pythonhosted.org/Markdown/extensions/code_hilite.html)
and [Fenced Code Blocks](http://pythonhosted.org/Markdown/extensions/fenced_code_blocks.html)
extensions.

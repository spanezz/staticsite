# staticsite

Static site generator.

Input:
 - a configuration file
 - markdown files
 - jinja2 templates
 - any other file copied verbatim

Output:
 - a site with the same structure as the input

## Dependencies

```bash
apt install python3-unidecode python3-markdown python3-toml python3-yaml python3-jinja2 python3-dateutil
```

[python-slugify](https://github.com/un33k/python-slugify) is currently not in
Debian, please package it. At the moment a copy of it is found in
`staticsite/slugify/`.

## Quick start

```bash
$ ./ssite build example
$ cd example/web
$ python -m SimpleHTTPServer
```

Then point your browser at <http://localhost:8000>.

## Semantic linking

All paths in the site material refer to elements in the site directory, and
will be adjusted to point to the generated content wherever it will be.

This allows to author content referring to other authored content regardless of
what the site generator implementation will decide to do with it later.


## Relative paths

Paths are resolved relative to the page first, and then going up the directory
hierarchy until the site root is reached. This allows to write content without
needing to worry about where it is in the site.


## Free structure

staticsite does not mandate a site structure, and simply generates output based
on where input files are found.


## Page metadata

TODO: Front matter syntax to be defined.

Well known metadata elements:

 - date: python datetime object, timezone aware
 - title: page title
 - tags: set of tag names
 - aliases: relative paths in the destination directory where the page should
   also show up

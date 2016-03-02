# staticsite

Static site generator.

Input:
 - a configuration file
 - markdown files
 - jinja2 templates
 - any other file that should be published as-is

Output:
 - a site with the same structure as the input

## Dependencies

```bash
apt install python3-pytz python3-unidecode python3-markdown python3-toml python3-yaml python3-jinja2 python3-dateutil python3-livereload
```

[python-slugify](https://github.com/un33k/python-slugify) is currently not in
Debian, please package it. At the moment a copy of it is found in
`staticsite/slugify/`.

## Quick start

```bash
$ ./ssite build example
$ cd example/web
$ python3 -m http.server 8000 --bind 127.0.0.1
```

or even just:

```bash
$ ./ssite serve example
```

Then point your browser at <http://localhost:8000>.


## Creating new posts

```bash
$ ./ssite new example
Please enter the post title: An example new post
(editor opens)
```

`staticsite` uses [Hugo-style archetypes](https://gohugo.io/content/archetypes/).

By default, `archetypes/default.md` is used as a template for new posts, and
you can use the `-a` or `--archetype` option to pick another one.

The archetype is processed via the same Jinja2 logic as the rest of the site,
plus the `title` and `slug` variables for the article. The `path` value in the
front matter is used to decide where to write the file, and is removed before
writing the post.

The editor and editor command line can also be configured, see
`global_settings.py` for details and examples.


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


## Settings

At the root of the site there is a configuration file called `settings.py` that
is interpreted via Python similarly to what happens in
[Django](https://docs.djangoproject.com/en/1.9/topics/settings/).

Only uppercase settings are used.

Default settings are defined in the module `staticsite/global_settings.py` and
overridden by `settings.py`.


## Markdown files

Markdown files have a `.md` extension and are prefixed by a [Hugo-style front
matter](https://gohugo.io/content/front-matter/).

The flavour of markdown is what's supported by
[python-markdown](http://pythonhosted.org/Markdown/) with the
[Extra](http://pythonhosted.org/Markdown/extensions/extra.html),
[CodeHilite](http://pythonhosted.org/Markdown/extensions/code_hilite.html)
and [Fenced Code Blocks](http://pythonhosted.org/Markdown/extensions/fenced_code_blocks.html)
extensions.

`staticsite` will postprocess the page contents to adjust internal links to
guarantee that they point where they should.


## Jinja2 files

Any files called `<name>.j2.<ext>` will be rendered with
[Jinja2](http://jinja.pocoo.org/) to generate `<name>.<ext>`.

This can be used to generate complex index pages, blog front pages, RSS2 and
Atom feeds, and anything Jinja2 is able to generate.


## Jinja2 environment

The `theme/` directory is in the Jinja2 search path, and you can `{% import %}`
or `{% include %}` anything from it.

Any setting defined in `settings.py` is also available to Jinja2, so you can do
for example:

```jinja2
<a class="navbar-brand" href="{{SITE_ROOT}}">{{SITE_NAME}}</a>
```

Extra functions provided to Jinja2 templates:

 * `url_for("path/page")`: returns the URL that links to the page or asset with
   the given path. The path is resolved relative to the current page, and if
   not found, relative to the parent page, and so on until the top.
 * `url_for(page)`: returns the URL that links to the given page.
 * `site_pages(path=None, limit=None, sort="-date")`: return a list of pages
   defined in the site that match the given arguments. `path` is a file glob
   (like `"blog/*"`) that matches the page file name. `limit` is the maximum
   number of pages to return. `sort` is the `page.meta` field to use to sort
   the pages. Prefix `sort` with a dash (`-`) for reverse sorting.
            now=self.generation_time,
 * `now`: the current date and time.

Extra filters provided to Jinja2 templates:

 * `|jinja2_datetime_format(format=None)` formats a datetime. Formats
   supported: "rss2", "rfc822", "atom", "rfc3339", "w3ctdf",
   "[iso8601](https://xkcd.com/1179/)" (default).

Each taxonomy defines extra `url_for_*` functions. For example, given a *tags*
taxonomy with *tag* as singular name:

 * `url_for_tags()`: links to the taxonomy index.
 * `url_for_tag(tag)`: links to the tag index.
 * `url_for_tag_archive(tag)`: links to the tag archive page.
 * `url_for_tag_rss(tag)`: links to the RSS2 feed for the tag.
 * `url_for_tag_atom(tag)`: links to the Atom feed for the tag.

When a `page` is passed to Jinja2, it has these members:

 * `page.meta`: all the metadata for the page, like `page.meta.title`,
   `page.meta.date`, `page.meta.tags` and anything else you have in the front
   matter.

When a `tag` (or other taxonomy element) is passed to Jinja2, it has these
members:

 * `tag.name`: the tag name
 * `tag.slug`: the [slug](https://en.wikipedia.org/wiki/Semantic_URL#Slug) for
   the tag
 * `tag.pages`: unordered list of pages with this tag


## Page metadata

The front matter of the post can be written in
[TOML](https://github.com/toml-lang/toml),
[YAML](https://en.wikipedia.org/wiki/YAML) or
[JSON](https://en.wikipedia.org/wiki/JSON), just like in
[Hugo](https://gohugo.io/content/front-matter/).

Well known metadata elements:

 - date: python datetime object, timezone aware
 - title: page title
 - tags: set of tag names
 - aliases: relative paths in the destination directory where the page should
   also show up


## Taxonomies

Any number of taxonomies, each described by a `<name>.taxonomy` file where it
should appear in the site.

See `example/site/tags.taxonomy` for details.

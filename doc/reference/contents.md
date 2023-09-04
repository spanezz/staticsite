# site: source contents of the site

staticsite does not mandate a site structure, and generates output mirroring
how source files are organised.

This lets you free to set the structure of your website by organising pages in
directories in any way you want.

Site contents can contain any kind of resource handled by staticsite
[features](feature.md), like:

* [markdown files](markdown.md)
* [restructuredText files](rst.rst)
* [data files](data.md)
* [jinja2 templates](jinja2.md)
* [taxonomy files](taxonomies.md)

Most pages handled by staticsite features will be generated as
`pagename/index.html` instead of `pagename.html`, to build a site with clean
URLs.

Any file not handled by staticsite features will be copied as-is to the
website, allowing you to intermix freely rendered pages with static assets or
downloadable content.


## Directory metadata

If a `.staticsite` file is found in a content directory, it is parsed as
`yaml`, `json`, or `toml`, and its contents become default
[metadata](metadata.md) for all the pages in that directory, and all its
subdirectories.

Likewise, the metadata found in the index file for a directory, become default
metadata for all the pages in that directory, and all its subdirectories.

You can use this to set metadata like `site_name`, `author`, `site_url`,
`site_root`.

Also, if you set `asset` to true in `.staticsite`, the subdirectory is loaded
as static files, and not passed through site features.

A `.staticsite` or directory index file can also have these entries to control
metadata of other files:

### `dirs`

Provides extra metadata for subdirectories of the given directory.

It is equivalent to setting `site` in each of the matching subdirectories.

### `files`

Provides extra metadata for files found in the directory.

This can be used, for example, to provide metadata for `.html` pages.

File names can be given as glob expressions or regular expressions, as with
[page selection](page-filter.md). If a file matches multiple entries, it gets
all the matching metadata, with the later ones potentially overwriting the
previous ones.

### `ignore`

Provides a list of expressions for ignoring files in this directory and all its
subdirectories.

The name of files to be ignored can be given as glob expressions or regular
expressions, as with [page selection](page-filter.md).

If you redefine `ignore` in a subdirectory, it *replaces* the setting in its
parent directories.

### Example directory metadata

```yaml
---
files:
  index.j2.html:
    syndication:
      filter:
        path: blog/*
        limit: 10
        sort: "-date"
      add_to:
        path: blog/*
      title: "Example blog feed"

dirs:
  "static-*:
      asset: true

ignore:
 - *.swp
 - *~
```


### Content loading

Content loading happens in 3 stages:

**scanning directories**: the content directory tree is scanned looking for
`.staticsite` files, directory index files, and taxonomy files, and using them
to build initial metadata for each file and directory in the site, and a list
of known taxonomies.

Other features could hook into this stage, like [`taxonomy`](taxonomies.md)
does, to gather information that can affect page loading.

For example, the list of taxonomies built at this stage informs which tags in
[reSt](rst.rst) files are parsed as lists of strings, and directory indices can
affect which files are loads as assets instead of as normal pages.

**loading content**: every file is scanned or loaded to contribute to the site
contents. Front matter metadata is loaded and validated.

**analyzing**: once content is loaded, features can have a pass at analyzing
the loaded data to generate, for example, tag pages, or syndication pages.

At this point, the site is laid out and all pages are ready to be rendered.


[Back to reference index](README.md)

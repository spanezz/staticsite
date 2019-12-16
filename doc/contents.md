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
* [jinja2 templates](j2.md)
* [taxonomy files](taxonomies.md)

Most pages handled by staticsite features will be generated as
`pagename/index.html` instead of `pagename.html`, to build a site with clean
URLs.

Any file not handled by staticsite features will be copied as-is to the
website, allowing you to intermix freely rendered pages with static assets or
downloadable content.


## Directory metadata

If a `.staticsite` file is found in a content directory, it is parsed as
`yaml`, `json`, or `toml`, and its contents are available to staticsite
features.

Entries currently supported:

* `files`: provides extra metadata for files found in the directory. This can
  be used, for example, to provide metadata for `.j2.html` pages.
  File names can be given as glob expressions or regular expressions, as with
  [page selection](page_filter.md)

Example directory metadata:

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
```

[Back to reference index](reference.md)

# Common page metadata

This is a list of metadata elements that have special meaning in this site.

You can use `ssite dump_meta` to see all the content and metadata that pages
make available to templates via the `page` variable.

<a name='template'>

### `template`


Template used to render the page. Defaults to `page.html`, although specific
pages of some features can default to other template names.

Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).

<a name='date'>

### `date`


Publication date for the page.

A python datetime object, timezone aware. If the date is in the future when
`ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
--draft` to also consider draft pages.

If missing, the modification time of the file is used.

<a name='author'>

### `author`

* Inherited from directory indices.

A string with the name of the author for this page.

SITE_AUTHOR is used as a default if found in settings.

If not found, it defaults to the current user's name.

<a name='template_copyright'>

### `template_copyright`

* Inherited from directory indices.
* Template for copyright

If set instead of `copyright`, it is a jinja2 template used to generate the
copyright information.

The template context will have `page` available, with the current page. The
result of the template will not be further escaped, so you can use HTML markup
in it.

If missing, defaults to `"© {{page.meta.date.year}} {{page.meta.author}}"`

<a name='copyright'>

### `copyright`

* Inherited from directory indices.

A string with the copyright information for this page.

<a name='template_title'>

### `template_title`

* Inherited from directory indices.
* Template for title

If set instead of `title`, it is a jinja2 template used to generate the title.
The template context will have `page` available, with the current page. The
result of the template will not be further escaped, so you can use HTML markup
in it.

<a name='title'>

### `title`

* Inherited from directory indices.

The page title.

If omitted:

 * the first title found in the page contents is used.
 * in the case of jinaj2 template pages, the contents of `{% block title %}`,
   if present, is rendered and used.
 * if the page has no title, the title of directory indices above this page is
   inherited.
 * if still no title can be found, the site name is used as a default.

<a name='template_description'>

### `template_description`

* Inherited from directory indices.
* Template for description

If set instead of `description`, it is a jinja2 template used to generate the
description. The template context will have `page` available, with the current
page. The result of the template will not be further escaped, so you can use
HTML markup in it.

<a name='description'>

### `description`

* Inherited from directory indices.

The page description. If omitted, the page will have no description.

<a name='site_name'>

### `site_name`

* Inherited from directory indices.

Name of the site. If missing, it defaults to the title of the toplevel index
page. If missing, it defaults to the name of the content directory.

<a name='site_url'>

### `site_url`

* Inherited from directory indices.

Base URL for the site, used to generate an absolute URL to the page.

<a name='site_path'>

### `site_path`


Where a content directory appears in the site.

By default, is is the `site_path` of the parent directory, plus the directory
name.

If you are publishing the site at `/prefix` instead of the root of the domain,
override this with `/prefix` in the content root.

<a name='build_path'>

### `build_path`


Relative path in the build directory for the file that will be written
when this page gets rendered. For example, `blog/2016/example.md`
generates `blog/2016/example/index.html`.

If found in pages front matter, it is ignored, and is always computed at page
load time.

<a name='asset'>

### `asset`

* Inherited from directory indices.

If set to True for a file (for example, by a `file:` pattern in a directory
index), the file is loaded as a static asset, regardless of whether a feature
would load it.

If set to True in a directory index, the directory and all its subdirectories
are loaded as static assets, without the interventions of features.

<a name='aliases'>

### `aliases`

* Inherited from directory indices.

Relative paths in the destination directory where the page should also show up.
[Like in Hugo](https://gohugo.io/extras/aliases/), this can be used to maintain
existing links when moving a page to a different location.

<a name='indexed'>

### `indexed`


If true, the page appears in [directory indices](dir.md) and in
[page filter results](page_filter.md).

It defaults to true at least for [Markdown](markdown.md),
[reStructuredText](rst.rst), and [data](data.md) pages.

<a name='draft'>

### `draft`


If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.

It defaults to false, or true if `page.meta.date` is in the future.

<a name='data_type'>

### `data_type`


Type of data for this file.

This is used to group data of the same type together, and to choose a
`data-[data_type].html` rendering template.

<a name='image'>

### `image`


Image used for this post.

It is set to a path to an image file relative to the current page.

During the analyze phase, it is resolved to the corresponding [image page](images.md).

If not set, and an image exists with the same name as the page (besides the
extension), that image is used.

<a name='pages'>

### `pages`


The `pages` metadata can use to select a set of pages shown by the current
page. Although default `page.html` template will not do anything with them,
other page templates, like `blog.html`, use this to select the pages to show.

The `pages` feature allows defining a [page filter](page-filter.md) in the
`pages` metadata element, which will be replaced with a list of matching pages.

To select pages, the `pages` metadata is set to a dictionary that select pages
in the site, with the `path`, and taxonomy names arguments similar to the
`site_pages` function in [templates](templates.md).

See [Selecting pages](page-filter.md) for details.

<a name='syndication'>

### `syndication`


Defines syndication for the contents of this page.

It is a structure which can contain normal metadata, plus:

* `add_to`: chooses which pages will include a link to the RSS/Atom feeds.
  By default, the link is added to all syndicated pages. If this is `False`,
  then no feed is added to pages. If it is a dictionary, it selects pages in
  the site, similar to the `site_pages` function in [templates](templates.md).
  See [Selecting pages](page-filter.md) for details.
* `archive`: if not false, an archive link will be generated next to the
  page. It can be set of a dictionary of metadata to be used as defaults for
  the generated archive page. It defaults to True.

Any other metadata found in the structure are used when generating pages for
the RSS/Atom feeds, so you can use `title`, `template_title`, `description`,
and so on, to personalize the feeds.

The pages that go in the feed are those listed in
[`page.meta.pages`](doc/reference/pages.md), keeping into account the
[`syndicated` and `syndication_date` page metadata](doc/reference/metadata.md).

When rendering RSS/Atom feed pages, `page.meta.pages` is replaced with the list
of syndicated pages, sorted with the most recent first.

Setting `syndication` to true turns on syndication with all defaults,
equivalent to:

```yaml
syndication:
  add_to: yes
  archive:
    template: archive.html
```

<a name='syndicated'>

### `syndicated`


Set to true if the page can be included in a syndication, else to false.

If not set, it defaults to the value of `indexed`.

<a name='syndication_date'>

### `syndication_date`


Syndication date for this page.

This is the date that will appear in RSS and Atom feeds, and the page will not
be syndicated before this date.

If a page is syndicated and `syndication_date` is missing, it defaults to `date`.

<a name='related'>

### `related`


Dict of pages related to this page.

Dict values will be resolved as pages.

If there are no related pages, `page.meta.related` will be guaranteed to exist
as an empty dictionary.

Features can add to this. For example, [syndication](syndication.md) can add
`meta.related.archive`, `meta.related.rss`, and `meta.related.atom`.

<a name='nav'>

### `nav`

* Inherited from directory indices.

List of page paths that are used for the navbar.

<a name='nav_title'>

### `nav_title`


Title to use when this paged is linked in a navbar.

It defaults to `page.meta.title`, or to the series name for series pages.

`nav_title` is only guaranteed to exist for pages that are used in `nav`.

# Common page metadata

This is a list of metadata elements that have special meaning in this site.

You can use `ssite dump_meta` to see all the content and metadata that pages
make available to templates via the `page` variable.

### `template`

Template used to render the page. Defaults to `page.html`, although specific
pages of some features can default to other template names.

Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).

### `date`

Publication date for the page.

A python datetime object, timezone aware. If the date is in the future when
`ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
--draft` to also consider draft pages.

If missing, the modification time of the file is used.

### `author`

*Inherited from directory indices.*

A string with the name of the author for this page.

SITE_AUTHOR is used as a default if found in settings.

### `copyright`

*Inherited from directory indices.*

A string with the copyright information for this page.

### `template_copyright`

*Inherited from directory indices.*

*Template version of `copyright`.*

If set instead of `copyright`, it is a jinja2 template used to generate the
copyright information.

The template context will have `page` available, with the current page. The
result of the template will not be further escaped, so you can use HTML markup
in it.

A good default can be:

```yaml
template_copyright: "© {{page.meta.date.year}} {{page.meta.author}}"
```

### `title`

*Inherited from directory indices.*

The page title.

If omitted:

 * the first title found in the page contents is used.
 * in the case of jinaj2 template pages, the contents of `{% block title %}`,
   if present, is rendered and used.
 * if the page has no title, the title of directory indices above this page is
   inherited.
 * if still no title can be found, the site name is used as a default.

### `template_title`

*Inherited from directory indices.*

*Template version of `title`.*

If set instead of `title`, it is a jinja2 template used to generate the title.
The template context will have `page` available, with the current page. The
result of the template will not be further escaped, so you can use HTML markup
in it.

### `description`

*Inherited from directory indices.*

The page description. If omitted, the page will have no description.

### `template_description`

*Inherited from directory indices.*

*Template version of `description`.*

If set instead of `description`, it is a jinja2 template used to generate the
description. The template context will have `page` available, with the current
page. The result of the template will not be further escaped, so you can use
HTML markup in it.

### `site_name`

*Inherited from directory indices.*

Name of the site. If missing, it defaults to the title of the toplevel index
page. If missing, it defaults to the name of the content directory.

### `site_url`

*Inherited from directory indices.*

Base URL for the site, used to generate an absolute URL to the page.

### `site_path`

*Inherited from directory indices.*

Where a content directory appears in the site.

By default, is is the `site_path` of the parent directory, plus the directory
name.

If you are publishing the site at `/prefix` instead of the root of the domain,
override this with `/prefix` in the content root.

### `build_path`

Relative path in the build directory for the file that will be written
when this page gets rendered. For example, `blog/2016/example.md`
generates `blog/2016/example/index.html`.

If found in pages front matter, it is ignored, and is always computed at page
load time.

### `asset`

*Inherited from directory indices.*

If set to True for a file (for example, by a `file:` pattern in a directory
index), the file is loaded as a static asset, regardless of whether a feature
would load it.

If set to True in a directory index, the directory and all its subdirectories
are loaded as static assets, without the interventions of features.

### `aliases`

Relative paths in the destination directory where the page should also show up.
[Like in Hugo](https://gohugo.io/extras/aliases/), this can be used to maintain
existing links when moving a page to a different location.

### `indexed`

If true, the page appears in [directory indices](dir.md) and in
[page filter results](page_filter.md).

It defaults to true at least for [Markdown](markdown.md),
[reStructuredText](rst.rst), and [data](data.md) pages.

### `draft`

If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.

It defaults to false, or true if `page.meta.date` is in the future.

### `data_type`

Type of data for this file.

This is used to group data of the same type together, and to choose a
`data-[data_type].html` rendering template.

### `image`

Image used for this post.

It is set to a path to an image file relative to the current page.

During the analyze phase, it is resolved to the corresponding [image page](images.md).

If not set, and an image exists with the same name as the page (besides the
extension), that image is used.

### `syndication`

Defines syndication for the contents of this page.

It is a structure which can contain various fields:

* `add_to`: chooses which pages will include a link to the RSS/Atom feeds
* `pages`: chooses which pages are shown in the RSS/Atom feeds

Any other metadata found in the structure are used when generating pages for
the RSS/Atom feeds, so you can use `title`, `template_title`, `description`,
and so on, to personalize the feeds.

`pages` and `add_to` are dictionaries that select pages in the site, similar
to the `site_pages` function in [templates](templates.md). See
[Selecting pages](page-filter.md) for details.

`pages` is optional, and if missing, `page.meta.pages` is used. Compared to
using the `pages` filter, using `syndication.pages` takes the
[`syndicated` and `syndication_date` page metadata](doc/reference/metadata.md) into account.

For compatibility, `filter` can be used instead of `pages`.

Before rendering, `pages` is replaced with the list of syndicated pages, sorted
with the most recent first.

### `syndicated`

Set to true if the page can be included in a syndication, else to false.

If not set, it defaults to the value of `indexed`.

### `syndication_date`

Syndication date for this page.

This is the date that will appear in RSS and Atom feeds, and the page will not
be syndicated before this date.

If a page is syndicated and `syndication_date` is missing, it defaults to `date`.

### `series`

List of categories for the `series` taxonomy.

Setting this as a simple string is the same as setting it as a list of one
element.

### `tags`

List of categories for the `tags` taxonomy.

Setting this as a simple string is the same as setting it as a list of one
element.

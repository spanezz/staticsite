# Common page metadata

This is a list of metadata elements that have special meaning in this site.

You can use `ssite dump_meta` to see all the content and metadata that pages
make available to templates via the `page` variable.

### template

Template used to render the page. Defaults to `page.html`, although specific
pages of some features can default to other template names.

Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).

### date

Publication date for the page.

A python datetime object, timezone aware. If the date is in the future when
`ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
--draft` to also consider draft pages.

If missing, the modification time of the file is used.

### author

*Inherited from directory indices.*

A string with the name of the author for this page.

### title

*Inherited from directory indices.*

The page title.

If omitted:

 * the first title found in the page contents is used.
 * in the case of jinaj2 template pages, the contents of `{% block title %}`,
   if present, is rendered and used.
 * if the page has no title, the title of directory indices above this page is
   inherited.
 * if still no title can be found, the site name is used as a default.

### template_title

*Inherited from directory indices.*

If set instead of title, it is a jinja2 template used to generate the title.
The template context will have `page` available, with the current page. The
result of the template will not be further escaped, so you can use HTML markup
in it.

### description

*Inherited from directory indices.*

The page description. If omitted, the page will have no description.

### template_description

*Inherited from directory indices.*

If set instead of description, it is a jinja2 template used to generate the
description. The template context will have `page` available, with the current
page. The result of the template will not be further escaped, so you can use
HTML markup in it.

### site_name

*Inherited from directory indices.*

Name of the site. If missing, it defaults to the title of the toplevel index
page. If missing, it defaults to the name of the content directory.

### site_url

*Inherited from directory indices.*

Base URL for the site, used to generate an absolute URL to the page.

### site_root

*Inherited from directory indices.*

Root directory of the site in URLs to the page.

If you are publishing the site at `/prefix` instead of the root of the domain,
override this with `/prefix`.

### asset

*Inherited from directory indices.*

If set to True for a file (for example, by a `file:` pattern in a directory
index), the file is loaded as a static asset, regardless of whether a feature
would load it.

If set to True in a directory index, the directory and all its subdirectories
are loaded as static assets, without the interventions of features.

### aliases

Relative paths in the destination directory where the page should also show up.
[Like in Hugo](https://gohugo.io/extras/aliases/), this can be used to maintain
existing links when moving a page to a different location.

### indexed

If true, the page appears in [directory indices](dir.md) and in
[page filter results](page_filter.md).

It defaults to true at least for [Markdown](markdown.md),
[reStructuredText](rst.rst), and [data](data.md) pages.

### syndication

Defines syndication for the contents of this page.

It is a structure which can contain various fields:

* `add_to`: chooses which pages will include a link to the RSS/Atom feeds
* `filter`: chooses which pages are shown in the RSS/Atom feeds

Any other metadata found in the structure are used when generating pages for
the RSS/Atom feeds, so you can use `title`, `template_title`, `description`,
and so on, to personalize the feeds.

`filter` and `add_to` are dictionaries that select pages in the site, similar
to the `site_pages` function in [templates](templates.md). See
[Selecting pages](page-filter.md) for details.

`filter` is optional, and if missing, `page.meta.pages` is used. This way,
[using the `pages` metadata](pages.md), you can define a single expression for
both syndication and page listing.

### series

List of categories for the `series` taxonomy.

Setting this as a simple string is the same as setting it as a list of one
element.

### tags

List of categories for the `tags` taxonomy.

Setting this as a simple string is the same as setting it as a list of one
element.

# taxonomy: Tag pages using one or more taxonomies.

## Page types

* [taxonomy](../pages/taxonomy.md): Root page for one taxonomy defined in the site
* [category](../pages/category.md): Index page showing all the pages tagged with a given taxonomy item

## Documentation

Files with a `.taxonomy` extension represent where that taxonomy will appear in
the built site.

For example, `dir/tags.taxonomy` will become `dir/tags/…` in the built site,
and contain an index of all categories in the taxonomy, and for each category
an index page, an archive page, and rss and atom feeds.

**Added in 1.3**: Removed again the need to list in [`TAXONOMIES` settings](../settings.md)
the taxonomies used in the site.

**Added in 1.2**: Any taxonomy you use needs to be explicitly listed in
settings as a `TAXONOMIES` list of taxonomy names. staticsite prints a warning
if a `.taxonomy` file is found that is not listed in `TAXONOMIES`.

The `.taxonomy` file will be a yaml, json, or toml file, like in
[markdown](../pages/markdown.md) front matter.

The relevant fields in a taxonomy file are:

* `title`, `description`: used for the taxonomy index page
* `category`: metadata for the page generated for each category in the taxonomy
* `archive`: metadata for the page generated for each category archive

* **changed in 1.2**: `template_tags`: use `template` instead
* **changed in 1.2**: `template_tag`: use `category/template` instead
* **changed in 1.2**: `template_archive`: use `archive/template` instead
* **Removed in 1.2**: `output_dir` is now ignored, and the taxonomy pages will
  be put in a directory with the same name as the file, without extension
* **Changed in 1.2**: `item_name` in a `.taxonomy` file does not have a special
  meaning anymore, and templates can still find it in the taxonomy page
  metadata
* **Added in 1.2**: page.meta["tags"] or other taxonomy names gets substituted,
  from a list of strings, to a list of pages for the taxonomy index, which can
  be used to generate links and iterate subpages in templates without the need
  of specialised functions.
* **Removed in 1.2**: `series_tags` is now ignored: every category can be used
  to build a series

Example:

```yaml
---
# In staticsite, a taxonomy is a group of attributes like categories or tags.
#
# Like in Hugo, you can have as many taxonomies as you want. See
# https://gohugo.io/taxonomies/overview/ for a general introduction to
# taxonomies.
#
# This file describes the taxonomy for "tags". The name of the taxonomy is
# taken from the file name.
#
# The format of the file is the same that is used for the front matter of
# posts, again same as in Hugo: https://gohugo.io/content/front-matter/

# Template for rendering the taxonomy index. Here, it's the page that shows the
# list of tags
template: taxonomy.html

category:
   # Template for rendering the page for one tag. Here, it's the page that shows
   # the latest pages tagged with the tag
   template: blog.html
   # Title used in category pages
   template_title: "Latest posts for tag <strong>{{page.name}}</strong>"
   # Description used in category pages
   template_description: "Most recent posts with tag <strong>{{page.name}}</strong>"

   syndication:
     add_to: no
     archive:
       # Template for rendering the archive page for one tag. Here, it's the page that
       # links to all the pages tagged with the tag
       template_title: "Archive of posts for tag <strong>{{page.name}}</strong>"
       template_description: "Archive of all posts with tag <strong>{{page.name}}</strong>"
```


### Jinja2 templates

Each taxonomy defines extra `url_for_*` functions. For example, given a *tags*
taxonomy with *tag* as singular name:

 * `taxonomies()`: list of all taxonomy index pages, ordered by name
 * `taxonomy(name)`: taxonomy index page for the given taxonomy
 * **Removed in 1.2**: `url_for_tags()`: links to the taxonomy index.
 * **Removed in 1.2**: `url_for_tag(tag)`: use `url_for(category)`
 * **Removed in 1.2**: `url_for_tag_archive(tag)`: use `url_for(category.archive)`
 * **Removed in 1.2**: `url_for_tag_rss(tag)`: see [the syndication feature](syndication.md)
 * **Removed in 1.2**: `url_for_tag_atom(tag)`: see [the syndication feature](syndication.md)

## Series of posts

Any category of any taxonomy collects an ordered list of posts, that can be
used to generate interlinked series of pages.

All posts in a category are ordered by date (see [page metadata](markdown.md)).

Given a [category page](taxonomies.md), the `.sequence(page)` method locates
the page in the sequence of pages in that category, returning a dictionary
with these values:

* `index`: position of this page in the series (starts from 1)
* `length`: number of pages in the series
* `first`: first page in the series
* `last`: last page in the series
* `prev`: previous page in the series, if available
* `next`: next page in the series, if available
* `title`: title for the series

This example template renders the position of the page in the series, choosing
as a series the first category of the page in a taxonomy called `series`:

```jinja2
{% with place = page.meta.series[0].sequence(page) %}
{{place.title}} {{place.index}}/{{place.length}}
{% endwith %}
```

### Series title

The series title is, by default, the title of the first page in the series.

If a page defines a `series_title` header, then it becomes the series title
from that page onwards. It is possible to redefine the series title during a
series, like for example a "My trip" series that later becomes "My trip:
Italy", "My trip: France", "My trip: Spain", and so on.

## Multiple series for a page

A page is part of one series for each category of each taxonomy it has.
Templates need to choose which categories are relevant for use in generating
series navigation links.

[Back to reference index](../README.md)

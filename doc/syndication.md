## Syndication

The Syndication feature implements generation of a [RSS](https://en.wikipedia.org/wiki/RSS)
and [Atom](https://en.wikipedia.org/wiki/Atom_(Web_standard\)) feed for a page
or group of pages.

Add a `syndication` metadata to a page to declare it as the index for a group
of page. RSS and Atom feeds will appear next to the page, containing pages
selected in the `syndication` metadata.

## Syndication metadata

Example `.staticsite` file alongside a blog index page (see [directory
metadata](contents.md)):

```yaml
---
files:
  index.html:
    syndication:
      filter:
        path: blog/*
        limit: 10
        sort: "-date"
      add_to:
        path: blog/*
      title: "Example blog feed"
```

`syndication` is placed alongside the usual [metadata](metadata.md),
and contains various fields:

* `filter`: chooses which pages are shown in the RSS/Atom feeds
* `add_to`: chooses which pages will include a link to the RSS/Atom feeds

Any other metadata are used when generating pages for the RSS/Atom feeds, so
you can use `title`, `template_title`, `description`, and so on, to personalize
the feeds.

`filter` and `add_to` are dictionaries that select pages in the site, similar
to the `site_pages` function in [templates](templates.md). See
[Selecting pages](page-filter.md) for details.

**Updated in 1.2**: `filter` is now optional, and if missing, `page.meta.pages`
is used. This way, [using the `pages` metadata](pages.md), you can define a
single expression for both syndication and page listing.

## Syndication of taxonomies

The syndication feature automatically turns each category of each taxonomy into
a syndication index, showing the pages with that category.

You can use the `syndication` metadata in your taxonomy categories to customize
titles and description in your categories feeds.


## Templates

See the example templates for working `syndication.rss` and `syndication.atom`
templates, that are used by the generated RSS and Atom pages.


## Syndication pages

RSS and Atom pages have these extra properties:

* `page.meta.date` is the most recent date of the pages in the feed
* `page.meta.index` is the page defining the syndication
* `page.pages` is a list of all the pages included in the syndication


[Back to reference index](reference.md)

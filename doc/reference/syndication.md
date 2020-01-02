## Syndication

The Syndication feature implements generation of a [RSS](https://en.wikipedia.org/wiki/RSS)
and [Atom](https://en.wikipedia.org/wiki/Atom_(Web_standard\)) feed for a page
or group of pages.

Add a `syndication` metadata to a page to declare it as the index for a group
of page. RSS and Atom feeds will appear next to the page, containing pages
selected in the `syndication` metadata.

## Syndication metadata

Example front page for a blog page:

```yaml
---
pages: blog/*
syndication: yes
template: blog.html
---
# My blog
```

See [metadata documentation](metadata.md) for a reference on the `syndication`
field.

## Syndication of taxonomies

Each category page in each taxonomy automatically defines a syndication
metadata equivalent to this:

```yaml
syndication:
  add_to: no
```

This would automatically generates RSS and Atom feeds with all pages in that
category, but those feed links will only be added to the category page itself.

You can use the `syndication` metadata in your taxonomy categories to customize
titles and description in your categories feeds, like with any other page.


## Templates

See the example templates for working `syndication.rss` and `syndication.atom`
templates, that are used by the generated RSS and Atom pages.

### `syndicated_pages(page=None, limit=None)`

Templates can use the `syndicated_pages` function to list syndicated pages for
a page, sorted with the most recently syndicated first.

`page` can be a page, a path to a page, or omitted, in which case the current
page is used. `page` can also be a list of pages, which will be sorted by
syndiaction date and sampled.

`limit` is the number of pages to return, or, if omitted, all the pages are
returned.

## Syndication pages

RSS and Atom pages have these extra properties:

* `page.meta.template` defaults to `syndication.rss` or `syndication.atom`
  instead of `page.html`
* `page.meta.date` is the most recent date of the pages in the feed
* `page.meta.index` is the page defining the syndication
* `page.meta.pages` is a list of all the pages included in the syndication


[Back to reference index](README.md)

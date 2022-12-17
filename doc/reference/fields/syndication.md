# syndication: Defines syndication for the contents of this page.

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

[Back to reference index](../README.md)

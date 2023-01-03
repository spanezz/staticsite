# related: Readonly mapping of pages related to this page, indexed by name.

If there are no related pages, `page.meta.related` will be guaranteed to exist
as an empty dictionary.

Features can add to this. For example, [syndication](syndication.md) can add
`meta.related.archive`, `meta.related.rss`, and `meta.related.atom`.

[Back to reference index](../README.md)

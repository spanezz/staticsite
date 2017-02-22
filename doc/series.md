# Series of posts

If `series` is part of a page metadata, then that page is considered part of an
ordered series of posts.

All posts in a series are ordered by date (see [page metadata](markdown.md)),
and can have links to the previous and next page in the series.

Each page in the series gets extra metadata, automatically computed:

 - `series_index`: position of this page in the series (starts from 1)
 - `series_length`: number of pages in the series
 - `series_first`: first page in the series
 - `series_last`: last page in the series
 - `series_prev`: previous page in the series, if available
 - `series_next`: next page in the series, if available
 - `series_title`: title for the series

`series_title`, by default, is the title of the first page in the series. It
can be changed by explicitly setting the `series_title` metadata on a page.

When a page defines a new value for `series_title`, all the following pages
will inherit it, until a page redefines it again.

A page can be part of only one series, to avoid the complexity of having to
deal with multiple previous/next links one for each series.

[Page templates](templates.md) in the series can check for the `series` and the
other `series_*` metadata to build navigation links for pages that are part of
a series.

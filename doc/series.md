# Series of posts

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

The series title is the title of the first page in the series.

A page is part of one series for each category of each taxonomy it has.
Templates need to choose which categories are relevant for use in generating
series navigation links.


[Back to reference index](reference.md)

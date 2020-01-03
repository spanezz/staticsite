# Tag site pages

You can tag site pages using one or more sets of categories. Each set of
categories is called a [taxonomy](../reference/taxonomies.md).

## Create a `tags` taxonomy

Write a a `tags.taxonomy` file:

```yaml
---
title: All tags
description: Index of all the tags used in the site
```

Here you can customize how the tag index looks like.

Each taxonomy automatically gets an index of all categories, and a little
blog-like page for each category, including RSS/Atom feeds and archive pages.


## Add the tags index to the site navbar

Change the [`nav`](about-page.md) entry to add a reference to `tags.taxonomy`:

~~~~{.md}
```yaml
nav: [tags.taxonomy, about.md]
```
~~~~


## Tag pages

You can now set the `tags` entry at the top of your posts to tag them:

~~~~{.md}
```yaml
tags: [travel, family]
```

# A day in the countryside

…
~~~~

## Next steps

* [Post series](post-series.md)
* [More HOWTOs](README.md)
* [Back to main documentation](../../README.md)

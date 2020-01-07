# Post series

Create a `series` [taxonomy](tag-pages.md) to group posts into sequential
series!

## Create a `series` taxonomy

Write a a `series.taxonomy` file:

```yaml
---
title: All series
description: Index of all the series of posts in this site
```

## Add pages to a series

You can now set the `tags` entry at the top of your posts to tag them:

~~~~{.md}
```yaml
series: venice2020
series_title: Venice 2020
```

# On the train to Venice

…
~~~~

`series` is just like any other taxonomy, but when the default page template
sees a category in the `series` taxonomy, it will use it to render *first*,
*last*, *previous*, and *next* navigation links.



## Next steps

* [Add an image for a post](post-image.md)
* [More HOWTOs](README.md)
* [Back to main documentation](../../README.md)


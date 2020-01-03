# Group blog posts in a directory

In the [blog tutorial](../tutorial/blog.md) all the posts are together at the
root of the site, and you are free to organise your site contents as you like.

Here are two examples:

## Posts in a `posts`/` directory

You can decide to write all your blog posts under a `posts/` directory. You can
then change the [`pages`](../reference/metadata.md#pages) selection accordingly
in the blog front matter:

~~~~{.md}
```yaml
site_url: https://www.example.org
template: blog.html
syndication: yes
pages: "posts/*"  # ← change like this so select only pages in posts/
```

# My new blog

Welcome to my new blog.
~~~~

The `pages` selection will pick all pages inside `posts/` and all its
subdirectories.


## Posts in a directory per year

You can decide to write all your blog posts under one directory per year, like
`2020/`, `2021`, and so on.

You can then change the [`pages`](../reference/metadata.md#pages) selection
to match directories consisting of numbers, using a regular expression:

~~~~{.md}
```yaml
site_url: https://www.example.org
template: blog.html
syndication: yes
pages: "^\\d+/"  # ← start with ^ to use a regular expression
```

# My new blog

Welcome to my new blog.
~~~~


## Next steps

* [Tag site pages](tag-pages.md)
* [More HOWTOs](README.md)
* [Back to main documentation](../../README.md)

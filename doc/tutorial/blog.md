# A new blog in under one minute

Create a new blog in few simple steps:

## Step 1: create `index.md`:

~~~~{.md}
```yaml
site_url: https://www.example.org
template: blog.html
syndication: yes
pages: "*"
```

# My new blog

Welcome to my new blog.
~~~~

## Step 2: run `ssite show`

A browser will open with a preview of your blog.


## Step 3: add posts

Create `new_post.md` and type something into it: as soon as you save it,
it will automatically appear in your blog.

Throw in a `new_post.jpg` to add an image to your new blog post.


## Step 4: publish your site

Run `ssite build -o built_site`

The contents of `built_site` are ready to be published by any web server.


## Next steps

* [See more tutorials](README.md)
* [Add an about page](../howto/about-page.md)
* [Group blog posts in a directory](../howto/blog-posts-in-a-directory.md)
* [Back to main documentation](../../README.md)

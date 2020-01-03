# Add an about page

## Write an about page

Create `about.md`:

~~~~{.md}
```yaml
nav_title: About
```
# About this site

> We have now sunk to a depth at which restatement of the obvious is the first
> duty of intelligent men. If liberty means anything at all, it means the right
> to tell people what they do not want to hear. In times of universal deceit,
> telling the truth will be a revolutionary act.
>
> (George Orwell)
~~~~

Add a [`nav` entry](../reference/metadata.md#nav) to `index.md`'s front matter:

~~~~{.md}
```yaml
site_url: https://www.example.org
template: blog.html
syndication: yes
pages: "*"
nav: [about.md]  # ← Add this!
```
~~~~

Now the navigation bar at the top of every page in the site will have an
"About" link.

You can change the `nav` setting at will, to customize navigation for the
various sections of your site.

You can use [`nav_title`](../reference/metadata.md#nav_title) to provide a
shorter title for the page when shown in a navbar.


## Next steps

* [More HOWTOs](README.md)
* [Back to main documentation](../../README.md)

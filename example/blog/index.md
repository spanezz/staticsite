---
syndication:
  pages:
    path: posts/*
  add_to:
    path: posts/*
  title: "My blog feed"
site_url: https://www.example.org
nav: [/index.md, /about.md]
template_copyright: "{% raw %}© {{page.meta.date.year}} {{page.meta.author}}{% endraw %}"
template: blog.html
---

# My example blog

Hello. These are the last 10 posts of my blog.

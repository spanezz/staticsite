## Subpages

The `pages` feature allows defining a [page filter](page-filter.md) in the
`pages` metadata element, which will be replaced with a list of matching pages.

To select pages, the `pages` metadata is set to a dictionaru that select pages
in the site, similar to the `site_pages` function in [templates](templates.md),
and to [`filter` in syndication](syndication.md). See [Selecting
pages](page-filter.md) for details.

## Example blog page

```jinja2
{% extends "base.html" %}

{% block front_matter %}
---
pages:
  path: blog/*
  limit: 10
  sort: "-date"
syndication:
  add_to:
    path: blog/*
  title: "Enrico's blog feed"
{% endblock %}
  
{% import 'blog.html' as blog %}
  
{% block title %}Enrico's blog{% endblock %}
  
{% block nav %}
{{super()}}
<li class="nav-item"><a class="nav-link" href="{{ url_for('/blog/archive.html') }}">Archive</a></li>
{% endblock %}

{% block content %}

<h1 class="display-4">Last 10 blog posts</h1>

{{blog.pages(page)}}

{% endblock %}
```


[Back to reference index](reference.md)

# pages: The `pages` metadata can use to select a set of pages shown by the current
page. Although default `page.html` template will not do anything with them,
other page templates, like `blog.html`, use this to select the pages to show.

The `pages` field allows defining a [page filter](../page-filter.md) which
will be replaced with a list of matching pages.

To select pages, the `pages` metadata is set to a dictionary that select pages
in the site, with the `path`, and taxonomy names arguments similar to the
`site_pages` function in [templates](../templates.md).

See [Selecting pages](../page-filter.md) for details.

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

{% import 'lib/blog.html' as blog %}

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

[Back to reference index](../README.md)

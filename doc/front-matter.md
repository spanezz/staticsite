# Front matter

Front matter in staticsite[^1] is arbitrary key/value data stored in
[JSON](https://en.wikipedia.org/wiki/JSON),
[YAML](https://en.wikipedia.org/wiki/YAML), or
[toml](https://en.wikipedia.org/wiki/TOML) format.

It is the way used to add metadata in [markdown](markdown.md),
[data](data.md), and [jinja2](jinja2.md) pages.

If metadata starts with `---`, it is read as YAML. If it starts with `+++` it
is read as TOML. If it starts with `{`, it is read as JSON.

For documentation on possible metadata contents, see [Common page metadata](metadata.md)

## Example YAML front matter in a markdown page

```yaml
---
title: Page with metadata in YAML format
---
page contents
```

## Example JSON front matter in a Jinja2 page

```jinja2
{% block front_matter %}
{
    "title": "Page with metadata in JSON format"
}
{% endblock %}

{% block content %}
...
{% endblock %}
```

## Example TOML data page

```toml
+++
title = "Page with metadata in TOML format"
```


[^1]:
Inspired from [Hugo front matter](https://gohugo.io/content/front-matter/)


[Back to reference index](reference.md)

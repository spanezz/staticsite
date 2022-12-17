# template_copyright: jinja2 template to use to generate `copyright` when it is not explicitly set.

The template context will have `page` available, with the current page. The
result of the template will not be further escaped, so you can use HTML markup
in it.

If missing, defaults to `"© {{meta.date.year}} {{meta.author}}"`

[Back to reference index](../README.md)

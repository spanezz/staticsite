# Data files

Data files have a `.json`, `.yaml`, or `.toml` extension and can be rendered
with custom Jinja2 templates.

The content of the data file is parsed, merged into the page metadata, and made
available to a jinja2 template as the `data` context variable. The jinja2
template can be chosen using the `type` metadata.

The result of the rendering is used as context for the `page.html` template, as
with markdown pages.

## Page metadata

The same metadata as with [markdown pages](markdown.md) can be used, plus the
following items:

 - `type`: the name of a Jinja2 template to load from the theme directory, as
   `data-[type].html`. If it is not found, `data.html` is tried for a generic
   template.

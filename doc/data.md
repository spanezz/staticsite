# Data files

Data files have a `.json`, `.yaml`, or `.toml` extension and can be rendered
with custom Jinja2 templates.

The content of the data file is parsed, merged into the page metadata, and made
available to a jinja2 template as the `data` context variable. The jinja2
template can be chosen using the `type` metadata.

The result of the rendering is used as context for the `page.html` template, as
with markdown pages.

## Page metadata

The [usual metadata](metadata.md) can be used, plus the following items:

### `page.meta.type`

Identifies the data type. Internally, the data feature groups data pages by
type, so further features can efficiently access thematic datasets.

The `page.meta.template` metadata for data pages, when not specified, defaults
to `dir-[type].html`, or if that is missing, to `data.html`.

### `page.data`

The data found in this page


[Back to reference index](reference.md)

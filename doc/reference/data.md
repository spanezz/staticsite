# Data files

Data files have a `.json`, `.yaml`, or `.toml` extension and can be rendered
with custom Jinja2 templates.

The content of the data file is parsed, and merged into the page metadata.

The jinja2 template can be chosen using the `data_type` metadata (see below).

The metadata of any page with the `data_type` metadata will be also tracked as
data. This allows to create normal pages that also add to a named dataset.

## Page metadata

The [usual metadata](metadata.md) can be used, plus the following items:

### `page.meta.data_type`

Identifies the data type. Internally, the data feature groups data pages by
type, so further features can efficiently access thematic datasets.

The `page.meta.template` metadata for data pages, when not specified, defaults
to `dir-[type].html`, or if that is missing, to `data.html`.


[Back to reference index](reference.md)

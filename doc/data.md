# Data files

Data files have a `.json`, `.yaml`, or `.toml` extension and can be rendered
with custom Jinja2 templates.

The content of the data file is parsed, and merged into the page metadata.

Data is extracted as the `data` element in the resulting metadata, and if there
is no data element, the whole metadata is taken as data.

Jinja2 templates can access the data as `page.data`.

The jinja2 template can be chosen using the `data_type` metadata (see below).

## Page metadata

The [usual metadata](metadata.md) can be used, plus the following items:

### `page.meta.data_type`

Identifies the data type. Internally, the data feature groups data pages by
type, so further features can efficiently access thematic datasets.

The `page.meta.template` metadata for data pages, when not specified, defaults
to `dir-[type].html`, or if that is missing, to `data.html`.

### `page.data`

The data found in this page.


[Back to reference index](reference.md)

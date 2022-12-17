# data_type: Type of data for this file.

Identifies the data type. Internally, the data feature groups data pages by
type, so further features can efficiently access thematic datasets.

This is used to group data of the same type together, and to choose a
`data-[data_type].html` rendering template.

The `page.meta.template` metadata for data pages, when not specified, defaults
to `dir-[type].html`, or if that is missing, to `data.html`.

[Back to reference index](../README.md)

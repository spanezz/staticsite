# data: Handle datasets in content directories.

## Page types

* [data](../pages/data.md): Data files

## Documentation

This allows storing pure-data datasets in JSON, Yaml, or Toml format in
the contents directory, access it from pages, and render it using Jinja2
templates.

Each dataset needs, at its toplevel, to be a dict with a ``type`` element,
and the dataset will be rendered using the ``data-{{type}}.html`` template.

Other front-matter attributes like ``date``, ``title``, ``aliases``, and
taxonomy names are handled as with other pages. The rest of the dictionary
is ignored and can contain any data one wants.

[Back to reference index](../README.md)

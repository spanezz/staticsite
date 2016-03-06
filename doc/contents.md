# site: contents of the site

staticsite does not mandate a site structure, and simply generates output based
on where input files are found inside `content` or any other directory you
configure in [settings.py](settings.md).

You can organise pages in directories in any way you want, and the structure of
the static site that will be generated will mirror the structure of pages in
`content`.

`content` can contain:

* [markdown files](markdown.md), with extension `.md`. `dir/file.md` will
  become `dir/file.html` in `web`.
* [jinja2 templates](templates.md) for arbitrary content, which contain `.j2`
  in their file name. `dir/file.j2.html` will become `dir/file.html` in `web`.
* [taxonomy files](taxonomies.md), with extension `.taxonomy`. Each taxonomy
  file represents one way to categorise your pages. `dir/tags.taxonomy` will
  become `dir/tags/…` in `web`, filled with an index for the whole taxonomy,
  one page per element in the taxonomy, rss and atom feeds, and archive pages.
* any other file will be copied as-is to `web`. `dir/file.jpg` will be
  copied as `dir/file.jpg` in `web`.

[Back to README](../README.md)

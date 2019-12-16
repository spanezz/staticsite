# Jinja2 pages

You can put [jinja2 templates](templates.md) in your site contents, and they
will be rendered as site pages.

This can be used to generate complex index pages, blog front pages, and
anything else [Jinja2](http://jinja.pocoo.org/) is able to generate.

You can set `JINJA2_PAGES` in the [site settings](settings.md) to a list of
patterns (globs or regexps as in [page filters](page-filter.md)) matching file
names to consider jinja2 templates by default. It defaults to
`["*.html", "*.j2.*"]`.

Any file with `.j2.` in their file name will be rendered as a template,
stripping `.j2.` in the destination file name.

For example, `dir/file.j2.html` will become `dir/file.html` when the site is
built.

[Back to reference index](reference.md)

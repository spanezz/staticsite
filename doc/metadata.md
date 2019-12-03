# Page metadata

This is a list of all metadata elements that are currently in use:

 - `template`: template used to render the page. Defaults to `page.html`,
   although specific pages of some features can default to other template
   names. Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/)
 - `date`: a python datetime object, timezone aware. If the date is in the
   future when `ssite` runs, the page will be consider a draft and will be
   ignored. Use `ssite --draft` to also consider draft pages.
 - `title`: the page title. If omitted, the first title found in the page is
   used. If the page has no title, the file name for the page will be used.
 - `template_title`: If set instead of title, it is a jinja2 template used to
   generate the title. The template context will have `page` available, with
   the current page. The result of the template will not be further escaped, so
   you can use HTML markup in it.
 - `description`: the page description. If omitted, the page will have no
   description.
 - `template_description`: If set instead of description, it is a jinja2
   template used to generate the description. The template context will have
   `page` available, with the current page. The result of the template will not
   be further escaped, so you can use HTML markup in it.
 - `tags`: list of tags for the page. If you define a new taxonomy, its name in
   the metadata will be used in the same way.
 - `aliases`: relative paths in the destination directory where the page should
   also show up. [Like in Hugo](https://gohugo.io/extras/aliases/), this can be
   used to maintain existing links when moving a page to a different location.
 - `series`: name identifying a [series of articles](series.md) that is article
   is a part of.
 - `series_title`, `series_prev`, `series_next`, `series_first`, `series_last`,
   `series_index`, `series_length`: see [series of articles](series.md)

[Back to README](../README.md)

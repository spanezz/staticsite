# Site

The [site object](../staticsite/site.py) collects and tracks all contents of a
site.

Through it, templates and code can access:

* `settings`: the site [settings](settings.md)
* `pages`: the site pages, indexed by relative path in the built site
* `timezone`: timezone object for the default site timezone, used as a default
  for naive datetime objects
* `generation_time`: datetime of the current execution of staticsite
* `theme`: [Theme](theme.md) for the site
* `features`: site [features](feature.md) indexed by name
* `content_root`: path to the root directory of site [contents](contents.md)
* `site_name`: configured site name
* `archetypes`: site [archetypes](archetypes.md)

[Back to reference index](reference.md)

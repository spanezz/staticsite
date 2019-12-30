# Directory indices

For each directory that does not have an index page, staticsite automatically
generates one: this makes every partial url to the site a valid URL.

## Directory pages

Directory pages have these extra properties:

* `page.meta.template` defaults to `dir.html`
* `page.meta.title` is the directory name, or the site name in case the site
  root is an autogenerated directory page
* `page.meta.pages` lists the pages in this directory
* `page.meta.parent` parent page in the directory hierarcny

[Back to reference index](README.md)
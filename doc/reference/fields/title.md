# title: Page title.

If missing:

 * it is generated via template_title, if present
 * the first title found in the page contents is used.
 * in the case of jinaj2 template pages, the contents of `{% block title %}`,
   if present, is rendered and used.
 * if the page has no title, the title of directory indices above this page is
   inherited.
 * if still no title can be found, the site name is used as a default.

[Back to reference index](../README.md)

# Constraints and invariants

**There is no need to rerender URLs to a page, unless the target file has
changed**

* A page's location does not change unless the file defining the page changes
* A reference to a page does not change unless the target file changes

**Jinja2 templates can only depend on page query expression of pages**

* TODO: log queries during jinja2 rendering
* TODO:remember what queries a template does, and use it to trigger
  rerenderings based on what changed


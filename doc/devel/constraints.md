# Constraints and invariants

**There is no need to rerender URLs to a page, unless the target file has
changed**

* A page's location does not change unless the file defining the page changes
* A reference to a page does not change unless the target file changes

**The rendered directory structure tracks the source directory structure**

* Paths in the source directory structure correspond to paths in the rendered
  directory structure
* The rendered directory structure can rename nodes (`index.md` ->
  `index.html`)
* The rendered directory structure can add paths (`foo.md` -> 'foo/index.html',
  or tag pages under a taxonomy root)
* The rendered directory structure can remove paths (for example, pruning empty
  directories)
* The rendered directory structure cannot move pages or directories up the
  directory structure (`/foo/bar.md` cannot become `/bar.md`, nor `/baz/bar.md`)
* When adding contents from multiple roots, the second root inherits the
  metadata and existing structure from the first one
* When adding contents from multiple roots, the second root cannot replace
  files from the first root

**Pages cannot determine the type of other pages**

* The type of a page is a function  only of its format, metadata, and the
  metadata of the directory that contains it.

**Jinja2 templates can only depend on page query expression of pages**

* TODO: log queries during jinja2 rendering
* TODO:remember what queries a template does, and use it to trigger
  rerenderings based on what changed


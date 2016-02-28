# staticsite

Static site generator.

Input:
 - a configuration file
 - markdown files
 - jinja2 templates
 - any other file copied verbatim

Output:
 - a site with the same structure as the input


## Semantic linking

All paths in the site material refer to elements in the site directory, and
will be adjusted to point to the generated content wherever it will be.

This allows to author content referring to other authored content regardless of
what the site generator implementation will decide to do with it later.


## Relative paths

Paths are resolved relative to the page first, and then going up the directory
hierarchy until the site root is reached. This allows to write content without
needing to worry about where it is in the site.


## Free structure

staticsite does not mandate a site structure, and simply generates output based
on where input files are found.

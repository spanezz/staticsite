#!/usr/bin/python3

import timeit
from staticsite.utils import yaml_codec  # noqa

test_yaml = """
---
# In staticsite, a taxonomy is a group of attributes like categories or tags.
#
# Like in Hugo, you can have as many taxonomies as you want. See
# https://gohugo.io/taxonomies/overview/ for a general introduction to
# taxonomies.
#
# This file describes the taxonomy for "tags". The name of the taxonomy is
# taken from the file name.
#
# The format of the file is the same that is used for the front matter of
# posts, again same as in Hugo: https://gohugo.io/content/front-matter/

# Any toplevel metadata is used for the tag index
title: "All series"
description: "Index of all series in the site."
# template: tags.html

# Category metadata is used for each tag page
category:
  # template: tag.html
  template_title: "Latest posts of series <strong>{{page.name}}</strong>"
  template_description: "Most recent posts of series <strong>{{page.name}}</strong>"
  syndication:
    template_title: "{{page.site.site_name}}: posts of series {{page.meta.index.name}}"
    template_description: "{{page.site.site_name}}: most recent posts of series {{page.meta.index.name}}"

# Archive metadata is used for each tag archive page
archive:
  # template: tag-archive.html
  template_title: "Archive of posts of series <strong>{{page.name}}</strong>"
  template_description: "Archive of all posts of series <strong>{{page.name}}</strong>"
"""

val = timeit.timeit("yaml_codec.loads_ruamel(test_yaml)", number=1000, globals=globals())
print(f"Ruamel: {val}")

val = timeit.timeit("yaml_codec.loads_pyyaml(test_yaml)", number=1000, globals=globals())
print(f"PyYAML: {val}")

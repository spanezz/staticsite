RestructuredText files
======================

RestructuredText files have a ``.rst`` extension and their metadata are taken
from docinfo information.

``staticsite`` will postprocess the RestructuredText doctree to adjust internal
links to guarantee that they point where they should.


Linking to other pages
----------------------

Pages can link to other pages via any of the normal reSt links.

Links that start with a ``/`` will be rooted at the top of the site contents.

Relative links are resolved relative to the location of the current page first,
and failing that relative to its parent directory, and so on until the root of
the site.

For example, if you have ``blog/2016/page.rst`` that contains a link to
``images/photo.jpg``, the link will point to the first of this
options that will be found:

1. ``blog/2016/images/photo.jpg``
2. ``blog/images/photo.jpg``
3. ``images/photo.jpg``

This allows to organise pages pointing to other pages or assets without needing
to worry about where they are located in the site.

You can link to other Markdown or RestructuredText pages with the ``.md`` or
``.rst`` extension (`like GitHub does`__)
or without, as if you were editing a wiki.

__ https://help.github.com/articles/relative-links-in-readmes/


Page metadata
-------------

The post metadata 

This is a list of all metadata elements that are currently in use:

 - ``date``: a python datetime object, timezone aware. If the date is in the
   future when ``ssite`` runs, the page will be consider a draft and will be
   ignored. Use `ssite --draft`` to also consider draft pages.
 - ``title``: the page title. If omitted, the first ``#`` title is used.
 - ``tags``: list of tags for the page. If you define a new taxonomy, its name in
   the metadata will be used in the same way.
 - ``aliases``: relative paths in the destination directory where the page should
   also show up. `Like in Hugo`__, this can be used to maintain existing links
   when moving a page to a different location.
 - ``series``: name identifying a `series of articles`_ that is article
   is a part of.
 - ``series_title``, ``series_prev``, ``series_next``, ``series_first``,
   ``series_last``, ``series_index``, ``series_length``: see `series of articles`_

__ https://gohugo.io/extras/aliases/
.. _series of articles: series.md

`Back to README <../README.md>`_

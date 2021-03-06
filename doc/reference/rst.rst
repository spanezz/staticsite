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

This allows organising pages pointing to other pages or assets without needing
to worry about where they are located in the site.

You can link to other Markdown or RestructuredText pages with the ``.md`` or
``.rst`` extension (`like GitHub does`__)
or without, as if you were editing a wiki.

__ https://help.github.com/articles/relative-links-in-readmes/


Page metadata
-------------

As in Sphinx_, a field list near the top of the file is parsed as front
matter and removed from the generated files.

.. _Sphinx: http://www.sphinx-doc.org/en/stable/markup/misc.html#file-wide-metadata

All `bibliographic fields`_ known to docutils are parsed according to their
respective type.

.. _`bibliographic fields`: http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#bibliographic-fields

All fields whose name matches a taxonomy defined in ``TAXONOMY_NAMES``
`settings <settings.md>`_ are parsed as yaml, and expected to be a list of
strings, with the set of values (e.g. tags) of the given taxonomy for the
current page.

See `page metadata <metadata.md>`_ for a list of commonly used metadata.


Rendering reStructuredText pages
--------------------------------

Besides the usual ``meta``, reStructuredText pages have also these attributes:

* ``page.contents``: the reSt contents rendered as HTML. You may want to use
  it with the [`|safe` filter](https://jinja.palletsprojects.com/en/2.10.x/templates/#safe)
  to prevent double escaping

`Back to reference index <reference.md>`_

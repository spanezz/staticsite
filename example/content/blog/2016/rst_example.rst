:date: 2016-04-16 10:23:00+02:00
:tags: example, "another tag"

Example blog post in reStructuredText
=====================================

This is an example blog post in |reST|_.

.. |reST| replace:: reStructuredText
.. _reST: http://docutils.sourceforge.net/rst.html

As in Sphinx_, a field list near the top of the file is parsed as front
matter and removed from the generated files.

.. _Sphinx: http://www.sphinx-doc.org/en/stable/markup/misc.html#file-wide-metadata

Syntax highlighting almost works (requires support in the stylesheet;
see the `docutils docs`_ for details), and line numbers can be added to
code snippets.

.. _`docutils docs`: http://docutils.sourceforge.net/docs/ref/rst/directives.html#code

.. code:: python
   :number-lines: 0

   import this

And also inline images work:

.. image:: example.png
   :alt: example image

(image from `wikimedia commons
<https://commons.wikimedia.org/wiki/File:Example_image.png>`_)

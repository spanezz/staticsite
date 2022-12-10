from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from . import fields

if TYPE_CHECKING:
    from .site import Site

log = logging.getLogger("metadata")


class SiteElement(metaclass=fields.FieldsMetaclass):
    """
    Functionality to expose a `meta` member giving dict-like access to Metadata
    fields
    """

    site_name = fields.Inherited(doc="""
        Name of the site. If missing, it defaults to the title of the toplevel index
        page. If missing, it defaults to the name of the content directory.
    """)
    site_url = fields.Inherited(doc="""
        Base URL for the site, used to generate an absolute URL to the page.
    """)
    author = fields.Inherited(doc="""
        A string with the name of the author for this page.

        SITE_AUTHOR is used as a default if found in settings.

        If not found, it defaults to the current user's name.
    """)

    template_copyright = fields.TemplateInherited(doc="""
        jinja2 template to use to generate `copyright` when it is not explicitly set.

        The template context will have `page` available, with the current page. The
        result of the template will not be further escaped, so you can use HTML markup
        in it.

        If missing, defaults to `"© {{meta.date.year}} {{meta.author}}"`
    """)

    template_title = fields.TemplateInherited(doc="""
        jinja2 template to use to generate `title` when it is not explicitly set.

        The template context will have `page` available, with the current page.
        The result of the template will not be further escaped, so you can use
        HTML markup in it.
    """)

    template_description = fields.TemplateInherited(doc="""
        jinja2 template to use to generate `description` when it is not
        explicitly set.

        The template context will have `page` available, with the current page.
        The result of the template will not be further escaped, so you can use
        HTML markup in it.
    """)

    asset = fields.Inherited(doc="""
        If set to True for a file (for example, by a `file:` pattern in a directory
        index), the file is loaded as a static asset, regardless of whether a feature
        would load it.

        If set to True in a directory index, the directory and all its subdirectories
        are loaded as static assets, without the interventions of features.
    """)

    def __init__(
            self,
            site: Site, *,
            parent: Optional[SiteElement] = None,
            meta_values: Optional[dict[str, Any]] = None):
        # Pointer to the root structure
        self.site = site

        if meta_values:
            self.update_meta(meta_values)
            # TODO: make update_meta pop values, then warn here about the
            # values that are left and will be ignored

        # Call fields to fill in computed fields
        for field in self._fields.values():
            field.fill_new(self, parent)

    def update_meta(self, values: dict[str, Any]):
        for field in self._fields.values():
            field.set(self, values)

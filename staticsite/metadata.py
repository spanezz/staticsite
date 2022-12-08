from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from . import fields

if TYPE_CHECKING:
    from .site import Site

log = logging.getLogger("metadata")


class FieldsMetaclass(type):
    """
    Allow a class to have a set of Field members, defining self-documenting
    metadata elements
    """
    def __new__(cls, name, bases, dct):
        _fields = {}

        # Add fields from subclasses
        for b in bases:
            if (b_fields := getattr(b, "_fields", None)):
                _fields.update(b_fields)

        # Add fields from the class itself
        for field_name, val in dct.items():
            if isinstance(val, fields.Field):
                # Store its description in the Model _meta
                _fields[field_name] = val
            else:
                # Leave untouched
                continue

        res = super().__new__(cls, name, bases, dct)
        res._fields = _fields
        return res


class Meta:
    """
    Read-only dict accessor to a SiteElement fields
    """
    def __init__(self, obj: SiteElement):
        self.obj = obj

    def __getitem__(self, key: str) -> Any:
        if key not in self.obj._fields:
            raise KeyError(key)

        try:
            return getattr(self.obj, key)
        except AttributeError:
            raise KeyError(key)

    def __contains__(self, key: str):
        if key not in self.obj._fields:
            return False

        return getattr(self.obj, key) is not None

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self.obj._fields:
            return default

        return getattr(self.obj, key, default)

    def to_dict(self) -> dict[str, Any]:
        """
        Return a dict with all the values of this Meta, including the inherited
        ones
        """
        res = {}
        for key in self.obj._fields:
            if (val := getattr(self.obj, key)) is not None:
                res[key] = val
        return res


class SiteElement(metaclass=FieldsMetaclass):
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

    date = fields.ElementDate(doc="""
        Publication date for the page.

        A python datetime object, timezone aware. If the date is in the future when
        `ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
        --draft` to also consider draft pages.

        If missing, the modification time of the file is used.
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

    draft = fields.Draft(doc="""
If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.

It defaults to false, or true if `meta.date` is in the future.
""")

    def __init__(
            self,
            site: Site, *,
            parent: Optional[SiteElement] = None,
            meta_values: Optional[dict[str, Any]] = None):
        # Pointer to the root structure
        self.site = site
        # The entry's metadata
        self.meta: Meta = Meta(self)

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

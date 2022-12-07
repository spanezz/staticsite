from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Optional, Union

import markupsafe

if TYPE_CHECKING:
    import jinja2

    from .site import Site


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
        for field_name, val in list(dct.items()):
            if isinstance(val, Metadata):
                # Store its description in the Model _meta
                _fields[field_name] = val
                val.name = field_name
            else:
                # Leave untouched
                continue

            # Remove field_name from class variables
            del dct[field_name]

        res = super().__new__(cls, name, bases, dct)
        res._fields = _fields
        return res


class Metadata:
    """
    Declarative description of a metadata element used by staticsite
    """

    def __init__(
            self,
            structure: bool = False,
            doc: str = ""):
        """
        :arg name: name of this metadata element
        :arg structure: set to True if this element is a structured value. Set
                        to false if it is a simple value like an integer or
                        string
        :arg doc: documentation for this metadata element
        """
        self.site: Site = None
        self.name: str
        # Type of this value
        self.type: str = "TODO"
        self.structure: bool = structure
        self.doc = inspect.cleandoc(doc)

    def get_notes(self):
        return ()

    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        """
        Compute values for the meta element of a newly created SiteElement
        """
        # By default, nothing to do
        pass

    def prepare_to_render(self, obj: SiteElement):
        """
        Compute values before the SiteElement gets rendered
        """
        pass

    def set(self, obj: SiteElement, values: dict[str, Any]):
        """
        Set metadata values in obj from values
        """
        # By default, plain assignment
        if self.name in values:
            obj.meta.values[self.name] = values[self.name]


class MetadataInherited(Metadata):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """

    def get_notes(self):
        yield from super().get_notes()
        yield "Inherited from parent pages"

    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        if parent is None:
            return
        if self.name not in obj.meta and self.name in parent.meta:
            obj.meta[self.name] = parent.meta[self.name]


class MetadataTemplateInherited(Metadata):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """
    def __init__(self, *args, template: str, **kw):
        """
        :arg template_for: set to the name of another field, it documents that
                           this metadata is a template version of another
                           metadata
        """
        super().__init__(*args, **kw)
        self.template: str = template
        self.type = "jinja2"

    def get_notes(self):
        yield from super().get_notes()
        yield "Inherited from parent pages"
        yield f"Template: {self.template}"

    def set_template(self, obj: SiteElement, tpl: Union[str, jinja2.Template]):
        if isinstance(tpl, str):
            obj.meta.values[self.template] = obj.site.theme.jinja2.from_string(tpl)
        else:
            obj.meta.values[self.template] = tpl

    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        if (tpl := obj.meta.get(self.template)):
            # Make sure the current template value is a compiled template
            if isinstance(tpl, str):
                obj.meta[self.template] = obj.site.theme.jinja2.from_string(tpl)
        elif parent is not None:
            # Try to inherit template
            if self.template not in obj.meta and (tpl := parent.meta.get(self.template)):
                obj.meta[self.template] = tpl

    def prepare_to_render(self, obj: SiteElement):
        if self.name in obj.meta:
            return

        if (template := obj.meta.get(self.template)) is not None:
            # If a template exists, render
            # TODO: remove meta= and make it compatibile again with stable staticsite
            val = markupsafe.Markup(template.render(meta=obj.meta, page=obj))
            obj.meta.values[self.name] = val
            return val

    def set(self, obj: SiteElement, values: dict[str, Any]):
        super().set(obj, values)
        # Also copy the template name
        if self.template in values:
            if isinstance(tpl := values[self.template], str):
                obj.meta.values[self.template] = obj.site.theme.jinja2.from_string(tpl)
            else:
                obj.meta.values[self.template] = tpl


class MetadataDate(Metadata):
    """
    Make sure, on page load, that the element is a valid aware datetime object
    """
    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        if (date := obj.meta.values.get(self.name)):
            obj.meta.values[self.name] = obj.site.clean_date(date)
        elif parent and (date := parent.meta.values.get(self.name)):
            obj.meta.values[self.name] = obj.site.clean_date(date)
        elif (src := getattr(obj, "src", None)) is not None and src.stat is not None:
            obj.meta.values[self.name] = obj.site.localized_timestamp(src.stat.st_mtime)
        else:
            obj.meta.values[self.name] = obj.site.generation_time


class MetadataIndexed(Metadata):
    """
    Make sure the field exists and is a bool, defaulting to False
    """
    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        val = obj.meta.get(self.name, False)
        if isinstance(val, str):
            val = val.lower() in ("yes", "true", "1")
        obj.meta[self.name] = val


class MetadataDraft(Metadata):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        # if obj.__class__.__name__ not in ("Asset", "Node"):
        #     print(f"MetadataDraft {obj.__class__=} {obj.meta=} {obj.site.generation_time=}"
        #           f" {obj.meta.values['date'] > obj.site.generation_time}")
        if (value := obj.meta.get(self.name)) is None:
            obj.meta.values[self.name] = obj.meta.values["date"] > obj.site.generation_time
        elif not isinstance(value, bool):
            obj.meta.values[self.name] = bool(value)


class MetadataDefault(Metadata):
    """
    Metadata with a default value when not set
    """
    def __init__(self, name, default, **kw):
        super().__init__(name, **kw)
        self.default = default

    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        if self.name not in obj.meta:
            obj.meta.values[self.name] = self.default


class Meta:
    """
    Holder for metadata values.

    Note that, compared to a dict, a value of None is considered the same as
    missing, in order to cache locally an inherited value that is missing from
    the parents.

    You can use something like False or the empty string as alternatives for
    None
    """
    def __init__(self):
        self.values: dict[str, Any] = {}

    def _deduplicated_repr(self, seen: set[str]):
        values = {}
        for k, v in self.values.items():
            if k in seen:
                continue
            seen.add(k)
            if isinstance(v, Meta):
                values[k] = "<Meta>"
            else:
                values[k] = v
        return f"{values!r}"

    def __repr__(self):
        return self._deduplicated_repr(set())

    def __getitem__(self, key: str) -> Any:
        """
        Lookup one metadata element
        """
        if key in self.values:
            return self.values[key]
        else:
            raise KeyError(key)

    def __setitem__(self, key: str, value: Any):
        """
        Set one metadata element
        """
        self.values[key] = value

    def __contains__(self, key: str):
        if key in self.values:
            return True
        else:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Lookup one metadata element
        """
        return self.values.get(key, default)

    def setdefault(self, key: str, value: Any) -> Any:
        """
        Set a value unless it was locally set
        """
        return self.values.setdefault(key, value)

    def pop(self, key: str, *args) -> Any:
        """
        Remove and return a value, if it was locally set
        """
        return self.values.pop(key, *args)

    def update(self, values: dict[str, Any]):
        """
        Copy locally set values from another meta
        """
        self.values.update(values)

    def derive(self) -> Meta:
        """
        Create a Meta element derived from this one
        """
        return Meta()

    def to_dict(self) -> dict[str, Any]:
        """
        Return a dict with all the values of this Meta, including the inherited
        ones
        """
        return {k: v for k, v in self.values.items() if v is not None}


class SiteElement(metaclass=FieldsMetaclass):
    """
    Functionality to expose a `meta` member giving dict-like access to Metadata
    fields
    """

    site_name = MetadataInherited("site_name", doc="""
        Name of the site. If missing, it defaults to the title of the toplevel index
        page. If missing, it defaults to the name of the content directory.
    """)
    site_url = MetadataInherited("site_url", doc="""
        Base URL for the site, used to generate an absolute URL to the page.
    """)
    author = MetadataInherited("author", doc="""
        A string with the name of the author for this page.

        SITE_AUTHOR is used as a default if found in settings.

        If not found, it defaults to the current user's name.
    """)

    date = MetadataDate("date", doc="""
        Publication date for the page.

        A python datetime object, timezone aware. If the date is in the future when
        `ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
        --draft` to also consider draft pages.

        If missing, the modification time of the file is used.
    """)

    copyright = MetadataTemplateInherited("copyright", template="template_copyright", doc="""
        If `template_copyright` is set instead of `copyright`, it is a jinja2 template
        used to generate the copyright information.

        The template context will have `page` available, with the current page. The
        result of the template will not be further escaped, so you can use HTML markup
        in it.

        If missing, defaults to `"© {{meta.date.year}} {{meta.author}}"`
    """)

    title = MetadataTemplateInherited("title", template="template_title", doc="""
        The page title.

        If `template_title` is set instead of `title`, it is a jinja2 template used to
        generate the title. The template context will have `page` available, with the
        current page. The result of the template will not be further escaped, so you
        can use HTML markup
        in it.

        If omitted:

         * the first title found in the page contents is used.
         * in the case of jinaj2 template pages, the contents of `{% block title %}`,
           if present, is rendered and used.
         * if the page has no title, the title of directory indices above this page is
           inherited.
         * if still no title can be found, the site name is used as a default.
    """)

    description = MetadataTemplateInherited("description", template="template_description", doc="""
        The page description. If omitted, the page will have no description.

        If `template_description` is set instead of `description`, it is a jinja2
        template used to generate the description. The template context will have
        `page` available, with the current page. The result of the template will not be
        further escaped, so you can use HTML markup in it.
    """)

    asset = MetadataInherited("asset", doc="""
        If set to True for a file (for example, by a `file:` pattern in a directory
        index), the file is loaded as a static asset, regardless of whether a feature
        would load it.

        If set to True in a directory index, the directory and all its subdirectories
        are loaded as static assets, without the interventions of features.
    """)

    indexed = MetadataIndexed("indexed", doc="""
        If true, the page appears in [directory indices](dir.md) and in
        [page filter results](page_filter.md).

        It defaults to true at least for [Markdown](markdown.md),
        [reStructuredText](rst.rst), and [data](data.md) pages.
    """)

    draft = MetadataDraft("draft", doc="""
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
        self.meta: Meta

        if parent is None:
            self.meta = Meta()
        else:
            self.meta = parent.meta.derive()

        if meta_values:
            # TODO: switch to update_meta only, when we can map all metadata used by features
            self.update_meta(meta_values)
            for k, v in meta_values.items():
                if k not in self.meta.values:
                    self.meta.values[k] = v

        # Call fields to fill in computed fields
        for field in self._fields.values():
            field.fill_new(self, parent)

    def update_meta(self, values: dict[str, Any]):
        for field in self._fields.values():
            field.set(self, values)

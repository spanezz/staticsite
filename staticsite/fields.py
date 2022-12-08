from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Optional, Union

import markupsafe

if TYPE_CHECKING:
    import jinja2

    from .metadata import SiteElement
    from .site import Site


class Field:
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
            obj.meta[self.name] = values[self.name]


class Inherited(Field):
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


class TemplateInherited(Field):
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
            obj.meta[self.template] = obj.site.theme.jinja2.from_string(tpl)
        else:
            obj.meta[self.template] = tpl

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
            obj.meta[self.name] = val
            return val

    def set(self, obj: SiteElement, values: dict[str, Any]):
        super().set(obj, values)
        # Also copy the template name
        if self.template in values:
            if isinstance(tpl := values[self.template], str):
                obj.meta[self.template] = obj.site.theme.jinja2.from_string(tpl)
            else:
                obj.meta[self.template] = tpl


class Date(Field):
    """
    Make sure, on page load, that the element is a valid aware datetime object
    """
    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        if (date := obj.meta.get(self.name)):
            obj.meta[self.name] = obj.site.clean_date(date)
        elif parent and (date := parent.meta.get(self.name)):
            obj.meta[self.name] = obj.site.clean_date(date)
        elif (src := getattr(obj, "src", None)) is not None and src.stat is not None:
            obj.meta[self.name] = obj.site.localized_timestamp(src.stat.st_mtime)
        else:
            obj.meta[self.name] = obj.site.generation_time


class Indexed(Field):
    """
    Make sure the field exists and is a bool, defaulting to False
    """
    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        val = obj.meta.get(self.name, False)
        if isinstance(val, str):
            val = val.lower() in ("yes", "true", "1")
        obj.meta[self.name] = val


class Draft(Field):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        # if obj.__class__.__name__ not in ("Asset", "Node"):
        #     print(f"MetadataDraft {obj.__class__=} {obj.meta=} {obj.site.generation_time=}"
        #           f" {obj.meta['date'] > obj.site.generation_time}")
        if (value := obj.meta.get(self.name)) is None:
            obj.meta[self.name] = obj.meta["date"] > obj.site.generation_time
        elif not isinstance(value, bool):
            obj.meta[self.name] = bool(value)

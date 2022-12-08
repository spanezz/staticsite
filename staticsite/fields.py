from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Optional

import jinja2

if TYPE_CHECKING:
    from .metadata import SiteElement


class Field:
    """
    Declarative description of a metadata element used by staticsite
    """

    def __init__(
            self, *,
            structure: bool = False,
            doc: str = ""):
        """
        :arg name: name of this metadata element
        :arg structure: set to True if this element is a structured value. Set
                        to false if it is a simple value like an integer or
                        string
        :arg doc: documentation for this metadata element
        """
        self.name: str
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

    def _clean(self, onj: SiteElement, value: Any) -> Any:
        """
        Hook to allow to clean values before set
        """
        return value

    def set(self, obj: SiteElement, values: dict[str, Any]):
        """
        Set metadata values in obj from values
        """
        # By default, plain assignment
        if self.name in values:
            if (cleaned_value := self._clean(obj, values[self.name])) is not None:
                obj.meta[self.name] = cleaned_value


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


class TemplateInherited(Inherited):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """

    def _clean(self, obj: SiteElement, value: Any) -> jinja2.Template:
        # Make sure the template is compiled
        if isinstance(value, jinja2.Template):
            return value
        elif isinstance(value, str):
            return obj.site.theme.jinja2.from_string(value)
        else:
            raise ValueError(f"{value!r} is not a valid value for a template field")


class Date(Field):
    """
    Field containing a date
    """
    def _clean(self, obj: SiteElement, value: Any) -> jinja2.Template:
        return obj.site.clean_date(value)


class ElementDate(Date):
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


class Bool(Field):
    """
    Make sure the field is a bool, possibly with a default value
    """
    def __init__(
            self, *,
            default: Optional[bool] = None,
            **kw):
        super().__init__(**kw)
        self.default = default

    def _clean(self, obj: SiteElement, val: Any) -> bool:
        if val in (True, False):
            return val
        elif isinstance(val, str):
            return val.lower() in ("yes", "true", "1")
        else:
            raise ValueError(f"{val!r} is not a valid value for a bool field")

    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        if (val := obj.meta.get(self.name)) is not None:
            obj.meta[self.name] = self._clean(obj, val)
        elif self.default is not None:
            obj.meta[self.name] = self._clean(obj, self.default)


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

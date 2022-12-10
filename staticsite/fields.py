from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Optional, Type

import jinja2

if TYPE_CHECKING:
    from .metadata import SiteElement


class Field:
    """
    Declarative description of a metadata element used by staticsite
    """
    def __init__(
            self, *,
            default: Any = None,
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
        self.default: Any = default
        self.structure: bool = structure
        self.doc = inspect.cleandoc(doc)

    def get_notes(self):
        return ()

    def __set_name__(self, owner: Type[SiteElement], name: str) -> None:
        self.name = name

    def __get__(self, obj: SiteElement, type: Type = None) -> Any:
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj: SiteElement, value: Any) -> None:
        obj.__dict__[self.name] = self._clean(obj, value)

    def fill_new(self, obj: SiteElement, parent: Optional[SiteElement] = None):
        """
        Compute values for the meta element of a newly created SiteElement
        """
        # By default, nothing to do
        pass

    def _clean(self, obj: SiteElement, value: Any) -> Any:
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
                obj.__dict__[self.name] = cleaned_value


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
        if self.name not in obj.__dict__ and self.name in parent.__dict__:
            obj.__dict__[self.name] = parent.__dict__[self.name]


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
        if (val := obj.__dict__.get(self.name)) is not None:
            obj.__dict__[self.name] = self._clean(obj, val)
        elif self.default is not None:
            obj.__dict__[self.name] = self._clean(obj, self.default)


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
            if isinstance(val, Field):
                # Store its description in the Model _meta
                _fields[field_name] = val
            else:
                # Leave untouched
                continue

        res = super().__new__(cls, name, bases, dct)
        res._fields = _fields
        return res

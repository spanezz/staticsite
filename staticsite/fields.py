from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, Optional, Type

import jinja2

if TYPE_CHECKING:
    from .site import Site

log = logging.getLogger("fields")


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

    def __set_name__(self, owner: Type[FieldContainer], name: str) -> None:
        self.name = name

    def __get__(self, obj: FieldContainer, type: Type = None) -> Any:
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj: FieldContainer, value: Any) -> None:
        obj.__dict__[self.name] = self._clean(obj, value)

    def _clean(self, obj: FieldContainer, value: Any) -> Any:
        """
        Hook to allow to clean values before set
        """
        return value


class Inherited(Field):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """
    def get_notes(self):
        yield from super().get_notes()
        yield "Inherited from parent pages"

    def __get__(self, obj: FieldContainer, type: Type = None) -> Any:
        if self.name not in obj.__dict__:
            if obj._parent is not None and self.name in obj._parent._fields:
                value = getattr(obj._parent, self.name)
            else:
                value = self.default
            obj.__dict__[self.name] = value
            return value
        else:
            return obj.__dict__[self.name]


class TemplateInherited(Inherited):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """

    def _clean(self, obj: FieldContainer, value: Any) -> jinja2.Template:
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
    def _clean(self, obj: FieldContainer, value: Any) -> jinja2.Template:
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

    def _clean(self, obj: FieldContainer, val: Any) -> bool:
        if val in (True, False):
            return val
        elif isinstance(val, str):
            return val.lower() in ("yes", "true", "1")
        else:
            raise ValueError(f"{val!r} is not a valid value for a bool field")


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


class FieldContainer(metaclass=FieldsMetaclass):
    def __init__(
            self,
            site: Site, *,
            parent: Optional[FieldContainer] = None,
            **kw):
        # Reference to Site, so that fields can access configuration, template
        # compilers, and so on
        self.site = site
        # Reference to parent, for field inheritance
        self._parent = parent

        self.update_fields(kw)

    def update_fields(self, values: dict[str, Any]):
        for name, value in values.items():
            if name in self._fields:
                setattr(self, name, value)
            else:
                log.warning("%r: setting unknown field %s=%r", self, name, value)

from __future__ import annotations

import logging
from typing import (TYPE_CHECKING, Any, Generic, Iterable, Optional, Type,
                    TypeVar, cast)

import jinja2

if TYPE_CHECKING:
    import datetime

    from .site import Site

log = logging.getLogger("fields")

P = TypeVar("P", bound="FieldContainer")
V = TypeVar("V")


class Field(Generic[P, V]):
    """
    Declarative description of a metadata element used by staticsite
    """
    def __init__(
            self, *,
            default: Optional[V] = None,
            structure: bool = False,
            internal: bool = False,
            inherited: bool = False,
            doc: Optional[str] = None):
        """
        :arg name: name of this metadata element
        :arg default: default value when this field has not been set
        :arg structure: set to True if this element is a structured value. Set
                        to false if it is a simple value like an integer or
                        string
        :arg internal: field is for internal use only, and not exported to
                       pages
        :arg doc: documentation for this metadata element
        """
        self.name: str
        self.default: Optional[V] = default
        self.structure: bool = structure
        self.internal: bool = internal
        self.inherited: bool = inherited
        if doc is not None:
            self.__doc__ = doc

    def get_notes(self) -> Iterable[str]:
        if self.inherited:
            yield "Inherited from parent pages"

    def __set_name__(self, owner: Type[P], name: str) -> None:
        self.name = name

    def __get__(self, obj: P, type: Optional[Type[P]] = None) -> Optional[V]:
        if self.inherited:
            if self.name not in obj.__dict__:
                if obj._parent is not None and self.name in obj._parent._fields:
                    value = getattr(obj._parent, self.name)
                else:
                    value = self.default
                obj.__dict__[self.name] = value
                return cast(V, value)
            else:
                return cast(V, obj.__dict__[self.name])
        else:
            return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj: P, value: Any) -> None:
        obj.__dict__[self.name] = self._clean(obj, value)

    def _clean(self, obj: P, value: Any) -> V:
        """
        Hook to allow to clean values before set
        """
        raise NotImplementedError(f"{self.__class__.__name__}._clean for {obj!r}.{self.name} not implemented")


class Const(Field[P, V]):
    """
    Field that takes a const value once and never changes it
    """
    def __get__(self, obj: P, type: Optional[Type[P]] = None) -> V:
        if self.name not in obj.__dict__:
            raise RuntimeError(f"{obj!r}.{self.name} has not been set")
        return cast(V, obj.__dict__[self.name])

    def __set__(self, obj: P, value: Any) -> None:
        if self.name in obj.__dict__:
            raise RuntimeError(f"{obj!r}.{self.name} has already been set")
        obj.__dict__[self.name] = self._clean(obj, value)


class ConstTypeField(Const[P, V]):
    """
    Field containing a string
    """
    def __init__(self, *, cls: Type[V], **kw: Any):
        super().__init__(**kw)
        self.cls = cls

    def _clean(self, page: P, value: Any) -> V:
        if not isinstance(value, self.cls):
            raise TypeError(
                    f"invalid value of type {type(value)} for {page!r}.{self.name}:"
                    f" expecting {self.cls.__name__}")
        return value


class Template(Field[P, jinja2.Template]):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """
    def _clean(self, obj: P, value: Any) -> jinja2.Template:
        # Make sure the template is compiled
        if isinstance(value, jinja2.Template):
            return value
        elif isinstance(value, str):
            return obj.site.theme.jinja2.from_string(value)
        else:
            raise ValueError(f"{value!r} is not a valid value for a template field")


class Str(Field[P, str]):
    """
    Field containing a string
    """
    def _clean(self, obj: P, value: Any) -> str:
        return str(value)


class Int(Field[P, int]):
    """
    Field containing an integer
    """
    def _clean(self, obj: P, value: Any) -> int:
        return int(value)


class ConstInt(Const[P, int]):
    """
    Const field containing an integer
    """
    def _clean(self, obj: P, value: Any) -> int:
        return int(value)


class Float(Field[P, float]):
    """
    Field containing a date
    """
    def _clean(self, obj: P, value: Any) -> float:
        return float(value)


class Date(Field[P, "datetime.datetime"]):
    """
    Field containing a date
    """
    def _clean(self, obj: P, value: Any) -> datetime.datetime:
        return obj.site.clean_date(value)


class Bool(Field[P, bool]):
    """
    Make sure the field is a bool, possibly with a default value
    """
    def __init__(
            self, *,
            default: Optional[bool] = None,
            **kw: Any):
        super().__init__(**kw)
        self.default = default

    def _clean(self, obj: P, val: Any) -> bool:
        if isinstance(val, bool):
            return val
        elif isinstance(val, str):
            return val.lower() in ("yes", "true", "1")
        else:
            raise ValueError(f"{val!r} is not a valid value for a bool field")


class Dict(Field[P, dict[str, Any]]):
    """
    Make sure the field is a dict
    """
    def __get__(self, obj: P, type: Optional[Type[P]] = None) -> dict[str, Any]:
        if (value := obj.__dict__.get(self.name)) is None:
            value = {}
            obj.__dict__[self.name] = value
        return value

    def _clean(self, obj: P, value: Any) -> dict[str, Any]:
        """
        Hook to allow to clean values before set
        """
        if isinstance(value, dict):
            return value
        raise ValueError(f"{value!r} is not a valid value for a dict field")


class FieldsMetaclass(type):
    """
    Allow a class to have a set of Field members, defining self-documenting
    metadata elements
    """
    _fields: dict[str, Field[Any, Any]]

    def __new__(cls: Type[FieldsMetaclass], name: str, bases: tuple[type], dct: dict[str, Any]) -> FieldsMetaclass:
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
    _fields: dict[str, Field[Any, Any]]

    def __init__(
            self,
            site: Site, *,
            parent: Optional[FieldContainer] = None,
            **kw: Any):
        # Reference to Site, so that fields can access configuration, template
        # compilers, and so on
        self.site = site
        # Reference to parent, for field inheritance
        self._parent = parent

        self.update_fields(kw)

    def update_fields(self, values: dict[str, Any]) -> None:
        for name, value in values.items():
            if name in self._fields:
                setattr(self, name, value)
            else:
                log.warning("%r: setting unknown field %s=%r", self, name, value)

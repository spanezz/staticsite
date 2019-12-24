from __future__ import annotations
from typing import Any, Optional
import inspect
from . import site


class Metadata:
    """
    Declarative description of a metadata used by staticsite
    """

    def __init__(
            self, name,
            inherited: bool = False,
            structure: bool = False,
            template_for: Optional[str] = None,
            doc: str = ""):
        """
        :arg name: name of this metadata element
        :arg inherited: set to True if this metadata, when present in a
                        directory index, should be inherited by other files in
                        directories and subdirectories. False if it stays local
                        to the file.
        :arg structure: set to True if this element is a structured value. Set
                        to false if it is a simple value like an integer or
                        string
        :arg template_for: set to the name of another field, it documents that
                           this metadata is a template version of another
                           metadata
        :arg doc: documentation for this metadata element
        """
        self.site: "site.Site" = None
        self.name: str = name
        self.inherited: bool = inherited
        self.structure: bool = structure
        self.template_for: Optional[str] = template_for
        self.doc = inspect.cleandoc(doc)

    def clean_value(self, val: Any) -> Any:
        """
        Return a validated and cleaned version of this metadata
        """
        return val

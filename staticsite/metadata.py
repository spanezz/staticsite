from __future__ import annotations
from typing import Optional
import inspect
from . import site
from . import page


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

    def on_load(self, page: "page.Page"):
        """
        Cleanup hook for the metadata on page load
        """
        pass

    # Mark as a noop to avoid calling it for each page unless overridden
    on_load.skip = True

    def on_analyze(self, page: "page.Page"):
        """
        Cleanup hook for the metadata at the start of the analyze pass
        """
        pass

    # Mark as a noop to avoid calling it for each page unless overridden
    on_analyze.skip = True


class MetadataDate(Metadata):
    """
    Make sure, on page load, that the element is a valid aware datetime object
    """
    def on_load(self, page: "page.Page"):
        date = page.meta.get(self.name)
        if date is None:
            if page.src.stat is not None:
                page.meta[self.name] = self.site.localized_timestamp(page.src.stat.st_mtime)
            else:
                page.meta[self.name] = self.site.generation_time
        else:
            page.meta[self.name] = self.site.clean_date(date)

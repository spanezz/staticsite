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
        Cleanup hook for the metadata on page load.

        Hooks are run in the order they have been registered, which follows
        feature dependency order, meaning that hooks for one feature can
        depends on hooks for previous features to have been run
        """
        pass

    # Mark as a noop to avoid calling it for each page unless overridden
    on_load.skip = True

    def on_analyze(self, page: "page.Page"):
        """
        Cleanup hook for the metadata at the start of the analyze pass.

        Hooks are run in the order they have been registered, which follows
        feature dependency order, meaning that hooks for one feature can
        depends on hooks for previous features to have been run
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
            if page.src is not None and page.src.stat is not None:
                page.meta[self.name] = self.site.localized_timestamp(page.src.stat.st_mtime)
            else:
                page.meta[self.name] = self.site.generation_time
        else:
            page.meta[self.name] = self.site.clean_date(date)


class MetadataIndexed(Metadata):
    """
    Make sure the field exists and is a bool, defaulting to False
    """
    def on_load(self, page: "page.Page"):
        val = page.meta.get(self.name, False)
        if isinstance(val, str):
            val = val.lower() in ("yes", "true", "1")
        page.meta[self.name] = val


class MetadataDraft(Metadata):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def on_load(self, page: "page.Page"):
        draft = page.meta.get(self.name)
        if draft is None:
            page.meta["draft"] = page.meta["date"] > self.site.generation_time
        elif isinstance(draft, bool):
            pass
        else:
            page.meta["draft"] = bool(page.meta["draft"])

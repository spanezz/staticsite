from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from .page import Page
    from .site import Site


class Registry:
    """
    Metadata registry for a site
    """

    def __init__(self, site: Site):
        self.site = site

        # Map metadata names to their definitions
        self.registry: dict[str, "Metadata"] = {}

        # Functions called to copy entries to a derived page metadata
        self.derive_functions: list[Callable[Meta, Meta], None] = []

        # Functions called on a page to cleanup metadata on page load
        self.on_load_functions: list[Callable[Page], None] = []

        # Functions called on a page to cleanup metadata at the beginning of
        # the analyze pass
        self.on_analyze_functions: list[Callable[Page], None] = []

        # Functions called to tweak page content rendered from markdown/rst
        self.on_contents_rendered_functions: list[Callable[Page, str], str] = []

    def add(self, metadata: "Metadata"):
        metadata.site = self.site
        self.registry[metadata.name] = metadata

        if (derive := getattr(metadata, "derive", None)):
            if not getattr(derive, "skip", False):
                self.derive_functions.append(derive)

        if (on_load := getattr(metadata, "on_load", None)):
            if not getattr(on_load, "skip", False):
                self.on_load_functions.append(on_load)

        if (on_analyze := getattr(metadata, "on_analyze", None)):
            if not getattr(on_analyze, "skip", False):
                self.on_analyze_functions.append(on_analyze)

        if (on_contents_rendered := getattr(metadata, "on_contents_rendered", None)):
            if not getattr(on_contents_rendered, "skip", False):
                self.on_contents_rendered_functions.append(on_contents_rendered)

    def derive(self, meta: Meta) -> Meta:
        """
        Derive a new metadata dictionary from an existing one.

        This is used to create metadata entry for pages in a directory, or for
        subpages of pages
        """
        res: Meta = Meta(self, parent=meta)
        for f in self.derive_functions:
            f(meta.values, res.values)
        return res

    def on_load(self, page: Page):
        """
        Run on_load functions on the page
        """
        for f in self.on_load_functions:
            f(page)

    def on_analyze(self, page: Page):
        """
        Run on_analyze functions on the page
        """
        for f in self.on_analyze_functions:
            f(page)

    def on_contents_rendered(self, page: Page, rendered: str, **kw) -> str:
        """
        Run on_contents_rendered functions on the page
        """
        for f in self.on_contents_rendered_functions:
            rendered = f(page, rendered, **kw)
        return rendered

    def __getitem__(self, key: str) -> "Metadata":
        return self.registry[key]

    def items(self):
        return self.registry.items()

    def keys(self):
        return self.registry.keys()

    def values(self):
        return self.registry.values()


class Metadata:
    """
    Declarative description of a metadata element used by staticsite
    """

    def __init__(
            self, name,
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
        self.name: str = name
        # Type of this value
        self.type: str = "TODO"
        self.structure: bool = structure
        self.doc = inspect.cleandoc(doc)

    def get_notes(self):
        return ()

    def derive(self, src_meta: Meta, dst_meta: Meta):
        """
        Copy this metadata from src_meta to dst_meta, if needed
        """
        pass

    # Mark as a noop to avoid calling it for each page unless overridden
    derive.skip = True

    def on_load(self, page: Page):
        """
        Hook for the metadata on page load.

        Hooks are run in the order they have been registered, which follows
        feature dependency order, meaning that hooks for one feature can
        depends on hooks for previous features to have been run
        """
        pass

    # Mark as a noop to avoid calling it for each page unless overridden
    on_load.skip = True

    def on_analyze(self, page: Page):
        """
        Hook for the metadata at the start of the analyze pass.

        Hooks are run in the order they have been registered, which follows
        feature dependency order, meaning that hooks for one feature can
        depends on hooks for previous features to have been run
        """
        pass

    # Mark as a noop to avoid calling it for each page unless overridden
    on_analyze.skip = True

    def on_contents_rendered(self, page: Page, rendered: str, **kw) -> str:
        """
        Hook to potentially annotate page contents rendered from markdown/rst
        before it is passed to Jinja2
        """
        return rendered

    on_contents_rendered.skip = True


class MetadataInherited(Metadata):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """

    def get_notes(self):
        yield from super().get_notes()
        yield "Inherited from directory indices."

    def derive(self, src_meta: Meta, dst_meta: Meta):
        if self.name in dst_meta:
            return

        if (val := src_meta.get(self.name)) is None:
            return
        dst_meta[self.name] = val


class MetadataTemplateInherited(Metadata):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """
    def __init__(self, *args, template_for: Optional[str] = None, **kw):
        """
        :arg template_for: set to the name of another field, it documents that
                           this metadata is a template version of another
                           metadata
        """
        super().__init__(*args, **kw)
        self.template_for: Optional[str] = template_for
        self.type = "jinja2"

    def get_notes(self):
        yield from super().get_notes()
        yield "Inherited from directory indices."
        yield f"Template for {self.template_for}"

    def derive(self, src_meta: Meta, dst_meta: Meta):
        if self.name in dst_meta:
            return

        if (val := src_meta.get(self.name)) is None:
            return

        if isinstance(val, str):
            dst_meta[self.name] = self.site.theme.jinja2.from_string(val)
        else:
            dst_meta[self.name] = val

    def on_load(self, page: Page):
        """
        Hook for inheriting metadata entries from a parent page
        """
        import markupsafe

        # If template_for exists, no need to render anything
        if self.template_for in page.meta:
            return

        # Find template in page or in parent dir
        src = page.meta.get(self.name)
        if src is None:
            return

        if isinstance(src, str):
            src = self.site.theme.jinja2.from_string(src)

        page.meta[self.template_for] = markupsafe.Markup(page.render_template(src))


class MetadataDate(Metadata):
    """
    Make sure, on page load, that the element is a valid aware datetime object
    """
    def on_load(self, page: Page):
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
    def on_load(self, page: Page):
        val = page.meta.get(self.name, False)
        if isinstance(val, str):
            val = val.lower() in ("yes", "true", "1")
        page.meta[self.name] = val


class MetadataDraft(Metadata):
    """
    Make sure the draft exists and is a bool, computed according to the date
    """
    def on_load(self, page: Page):
        draft = page.meta.get(self.name)
        if draft is None:
            page.meta["draft"] = page.meta["date"] > self.site.generation_time
        elif isinstance(draft, bool):
            pass
        else:
            page.meta["draft"] = bool(page.meta["draft"])


class MetadataDefault(Metadata):
    """
    Metadata with a default value when not set
    """
    def __init__(self, name, default, **kw):
        super().__init__(name, **kw)
        self.default = default

    def on_load(self, page: Page):
        page.meta.setdefault(self.name, self.default)


class Meta:
    """
    Holder for metadata values
    """
    def __init__(self, registry: Registry, parent: Optional[Meta] = None):
        self.registry = registry
        self.parent = parent
        self.values: dict[str, Any] = {}

    def __repr__(self):
        return f"{self.values=!r},{self.parent=!r}"

    def __getitem__(self, key: str) -> Any:
        """
        Lookup one metadata element
        """
        return self.values[key]

    def __setitem__(self, key: str, value: Any):
        """
        Set one metadata element
        """
        self.values[key] = value

    def __contains__(self, key: str):
        return self.values.__contains__(key)

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
        return self.registry.derive(self)

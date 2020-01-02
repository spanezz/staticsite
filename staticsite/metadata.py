from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, List, Callable
import inspect

if TYPE_CHECKING:
    from .page import Page
    from .site import Site
    from .utils.typing import Meta


class Registry:
    """
    Metadata registry for a site
    """

    def __init__(self, site: Site):
        self.site = site

        self.registry: Dict[str, "Metadata"] = {}

        # Functions called on a page to cleanup metadata on page load
        self.on_load_functions: List[Callable[Page], None] = []

        # Functions called on a page to cleanup metadata at the beginning of
        # the analyze pass
        self.on_analyze_functions: List[Callable[Page], None] = []

        # Functions called when loading directory metadata
        self.on_dir_meta_functions: List[Callable[Page, Meta], None] = []

    def add(self, metadata: "Metadata"):
        metadata.site = self.site
        self.registry[metadata.name] = metadata

        on_load = getattr(metadata, "on_load", None)
        if not getattr(on_load, "skip", False):
            self.on_load_functions.append(on_load)

        on_analyze = getattr(metadata, "on_analyze", None)
        if not getattr(on_analyze, "skip", False):
            self.on_analyze_functions.append(on_analyze)

        on_dir_meta = getattr(metadata, "on_dir_meta", None)
        if not getattr(on_dir_meta, "skip", False):
            self.on_dir_meta_functions.append(on_dir_meta)

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

    def on_dir_meta(self, page: Page, meta: Meta):
        """
        Run on_dir_meta functions on the page
        """
        for f in self.on_dir_meta_functions:
            f(page, meta)

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
    Declarative description of a metadata used by staticsite
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

    def on_load(self, page: Page):
        """
        Cleanup hook for the metadata on page load.

        Hooks are run in the order they have been registered, which follows
        feature dependency order, meaning that hooks for one feature can
        depends on hooks for previous features to have been run
        """
        pass

    # Mark as a noop to avoid calling it for each page unless overridden
    on_load.skip = True

    def on_analyze(self, page: Page):
        """
        Cleanup hook for the metadata at the start of the analyze pass.

        Hooks are run in the order they have been registered, which follows
        feature dependency order, meaning that hooks for one feature can
        depends on hooks for previous features to have been run
        """
        pass

    # Mark as a noop to avoid calling it for each page unless overridden
    on_analyze.skip = True

    def on_dir_meta(self, page: Page, meta: Meta):
        """
        Hook to potentially transfer metadata from what is found in a directory
        index page to the directory metadata
        """
        pass

    on_dir_meta.skip = True


class MetadataInherited(Metadata):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """

    def get_notes(self):
        yield from super().get_notes()
        yield "Inherited from directory indices."

    def _inherit(self, page: Page):
        if self.name in page.meta:
            return

        parent = page.dir
        if parent is None:
            return

        val = parent.meta.get(self.name)
        if val is None:
            return
        page.meta[self.name] = val

    def on_load(self, page: Page):
        """
        Hook for inheriting metadata entries from a parent page
        """
        self._inherit(page)

    def on_dir_meta(self, page: Page, meta: Meta):
        """
        Inherited metadata are copied from directory indices into directory
        metadata
        """
        if self.name not in meta:
            return
        page.meta[self.name] = meta[self.name]


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

    def _inherit(self, page: Page):
        if self.name in page.meta:
            return

        parent = page.dir
        if parent is None:
            return

        val = parent.meta.get(self.name)
        if val is None:
            return
        page.meta[self.name] = val

    def on_load(self, page: Page):
        """
        Hook for inheriting metadata entries from a parent page
        """
        import jinja2
        self._inherit(page)

        src = page.meta.get(self.name)
        if src is None:
            return

        if self.template_for in page.meta:
            return

        if isinstance(src, str):
            src = self.site.theme.jinja2.from_string(src)
            page.meta[self.name] = src
        page.meta[self.template_for] = jinja2.Markup(page.render_template(src))

    def on_dir_meta(self, page: Page, meta: Meta):
        """
        Inherited metadata are copied from directory indices into directory
        metadata
        """
        if self.name not in meta:
            return
        page.meta[self.name] = meta[self.name]


class MetadataSitePath(Metadata):
    def on_dir_meta(self, page: Page, meta: Meta):
        """
        Inherited metadata are copied from directory indices into directory
        metadata
        """
        if self.name not in meta:
            return
        page.meta[self.name] = meta[self.name]


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

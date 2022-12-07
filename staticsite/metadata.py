from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

import markupsafe

if TYPE_CHECKING:
    import jinja2

    from .page import Page
    from .site import Site


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
        for field_name, val in list(dct.items()):
            if isinstance(val, Metadata):
                # Store its description in the Model _meta
                _fields[field_name] = val
                # val.set_name(field_name)
            else:
                # Leave untouched
                continue

            # Remove field_name from class variables
            del dct[field_name]

        res = super().__new__(cls, name, bases, dct)
        res._fields = _fields
        return res


class Registry:
    """
    Metadata registry for a site
    """

    def __init__(self, site: Site):
        self.site = site

        # Map metadata names to their definitions
        self.registry: dict[str, "Metadata"] = {}

        # Functions called to copy entries to a derived page metadata
        self.derive_functions: dict[str, Callable[[Meta, dict[str, Any]], None]] = {}

        # Functions called on a page to cleanup metadata on page load
        self.on_load_functions: list[Callable[Page], None] = []

    def add(self, metadata: "Metadata"):
        metadata.site = self.site
        self.registry[metadata.name] = metadata

        if (derive := getattr(metadata, "derive", None)):
            if not getattr(derive, "skip", False):
                self.derive_functions[metadata.name] = derive

        if (on_load := getattr(metadata, "on_load", None)):
            if not getattr(on_load, "skip", False):
                self.on_load_functions.append(on_load)

    def on_load(self, page: Page):
        """
        Run on_load functions on the page
        """
        for f in self.on_load_functions:
            f(page)

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

    def fill_new(self, obj: MetaMixin, parent: Optional[MetaMixin] = None):
        """
        Compute values for the meta element of a newly created MetaMixin
        """
        # By default, nothing to do
        pass

    def derive(self, meta: Meta):
        """
        Copy this metadata from src_meta to dst_meta, if needed
        """
        # By default, nothing to do
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


class MetadataInherited(Metadata):
    """
    This metadata, when present in a directory index, should be inherited by
    other files in directories and subdirectories.
    """

    def get_notes(self):
        yield from super().get_notes()
        yield "Inherited from parent pages"

    def fill_new(self, obj: MetaMixin, parent: Optional[MetaMixin] = None):
        if parent is None:
            return
        if self.name not in obj.meta and self.name in parent.meta:
            obj.meta[self.name] = parent.meta[self.name]

    def derive(self, meta: Meta):
        if meta.parent is None:
            return None
        meta.values[self.name] = val = meta.parent.get(self.name)
        return val


class MetadataTemplateInherited(Metadata):
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

    def set_template(self, obj: MetaMixin, tpl: Union[str, jinja2.Template]):
        if isinstance(tpl, str):
            obj.meta.values[self.template] = obj.site.theme.jinja2.from_string(tpl)
        else:
            obj.meta.values[self.template] = tpl

    def fill_new(self, obj: MetaMixin, parent: Optional[MetaMixin] = None):
        # Inherit template
        if parent is not None:
            if self.template not in obj.meta and (tpl := parent.meta.values.get(self.template)):
                self.set_template(obj, tpl)

        if self.name in obj.meta:
            return

        # TODO: do the rendering before the page is rendered, not at instantiation time
        if (template := obj.meta.get(self.template)) is not None:
            # If a template exists, render
            val = markupsafe.Markup(template.render(meta=obj.meta, page={"meta": obj.meta}))
            obj.meta.values[self.name] = val
            return val
        elif parent is not None and self.name in parent.meta:
            # Else fallback to plain inheritance
            obj.meta.values[self.name] = parent.meta[self.name]

    def lookup_template(self, meta: Meta) -> Optional[jinja2.Template]:
        """
        Recursively find a template in meta or its parents
        """
        if (val := meta.values.get(self.template)):
            if isinstance(val, str):
                compiled = self.site.theme.jinja2.from_string(val)
                # Replace with a compiled version, to need to compile it only
                # once
                meta.values[self.template] = compiled
                return compiled
            else:
                return val
        if meta.parent is None:
            return None
        return self.lookup_template(meta.parent)

    def derive(self, meta: Meta):
        # If a template exists, render without looking for a parent element
        if (template := self.lookup_template(meta)) is not None:
            val = markupsafe.Markup(template.render(meta=meta, page={"meta": meta}))
            meta.values[self.name] = val
            return val

        # Else fallback to plain inheritance
        if meta.parent is None:
            return None
        meta.values[self.name] = val = meta.parent.get(self.name)
        return val


class MetadataDate(Metadata):
    """
    Make sure, on page load, that the element is a valid aware datetime object
    """
    def fill_new(self, obj: MetaMixin, parent: Optional[MetaMixin] = None):
        if (date := obj.meta.values.get(self.name)):
            obj.meta.values[self.name] = obj.site.clean_date(date)
        elif parent and (date := parent.meta.values.get(self.name)):
            obj.meta.values[self.name] = obj.site.clean_date(date)
        elif (src := getattr(obj, "src", None)) is not None and src.stat is not None:
            obj.meta.values[self.name] = obj.site.localized_timestamp(src.stat.st_mtime)
        else:
            obj.meta.values[self.name] = obj.site.generation_time

    def on_load(self, page: Page):
        date = page.meta.values.get(self.name)
        if date is None:
            if page.src is not None and page.src.stat is not None:
                page.meta.values[self.name] = self.site.localized_timestamp(page.src.stat.st_mtime)
            else:
                page.meta.values[self.name] = self.site.generation_time
        else:
            page.meta.values[self.name] = self.site.clean_date(date)


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
    def fill_new(self, obj: MetaMixin, parent: Optional[MetaMixin] = None):
        if (value := obj.meta.get(self.name)) is None:
            obj.meta.values[self.name] = obj.meta.values["date"] > obj.site.generation_time
        elif not isinstance(value, bool):
            obj.meta.values[self.name] = bool(value)


class MetadataDefault(Metadata):
    """
    Metadata with a default value when not set
    """
    def __init__(self, name, default, **kw):
        super().__init__(name, **kw)
        self.default = default

    def fill_new(self, obj: MetaMixin, parent: Optional[MetaMixin] = None):
        if self.name not in obj.meta:
            obj.meta.values[self.name] = self.default

    def on_load(self, page: Page):
        page.meta.setdefault(self.name, self.default)


class Meta:
    """
    Holder for metadata values.

    Note that, compared to a dict, a value of None is considered the same as
    missing, in order to cache locally an inherited value that is missing from
    the parents.

    You can use something like False or the empty string as alternatives for
    None
    """
    def __init__(self, registry: Registry, parent: Optional[Meta] = None):
        self.registry = registry
        self.parent = parent
        self.values: dict[str, Any] = {}

    def _deduplicated_repr(self, seen: set[str]):
        values = {}
        for k, v in self.values.items():
            if k in seen:
                continue
            seen.add(k)
            if isinstance(v, Meta):
                values[k] = "<Meta>"
            else:
                values[k] = v
        if self.parent is not None:
            return f"({values!r}, parent={self.parent._deduplicated_repr(seen)})"
        else:
            return f"{values!r}"

    def __repr__(self):
        return self._deduplicated_repr(set())

    def __getitem__(self, key: str) -> Any:
        """
        Lookup one metadata element
        """
        if key not in self.values:
            if (derive := self.registry.derive_functions.get(key)) is None:
                # It cannot be inherited
                raise KeyError(key)
            if self.parent is None:
                # There is no parent to inherit this from
                raise KeyError(key)
            if (val := derive(self)) is None:
                # Derivation returned a missing
                raise KeyError(key)
            return val
        elif (val := self.values[key]) is not None:
            # A None is a cached failed derivation
            return val
        else:
            raise KeyError(key)

    def __setitem__(self, key: str, value: Any):
        """
        Set one metadata element
        """
        self.values[key] = value

    def __contains__(self, key: str):
        if key not in self.values:
            if (derive := self.registry.derive_functions.get(key)) is None:
                # It cannot be inherited
                return False
            if self.parent is None:
                # There is no parent to inherit this from
                return False
            if derive(self) is None:
                # Derivation returned a missing
                return False
            return True
        elif self.values[key] is not None:
            return True
        else:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Lookup one metadata element
        """
        if key not in self.values:
            if (derive := self.registry.derive_functions.get(key)) is None:
                # It cannot be inherited
                return default
            if self.parent is None:
                # There is no parent to inherit this from
                return default
            if (val := derive(self)) is None:
                # Derivation returned a missing
                return default
            return val
        elif (val := self.values[key]) is not None:
            # A None is a cached failed derivation
            return val
        else:
            return default

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
        return Meta(self.registry, parent=self)

    def to_dict(self) -> dict[str, Any]:
        """
        Return a dict with all the values of this Meta, including the inherited
        ones
        """
        # Resolve all derived values
        for name, func in self.registry.derive_functions.items():
            if name not in self.values:
                func(self)

        return {k: v for k, v in self.values.items() if v is not None}


class PageAndNodeFields(metaclass=FieldsMetaclass):
    site_name = MetadataInherited("site_name", doc="""
        Name of the site. If missing, it defaults to the title of the toplevel index
        page. If missing, it defaults to the name of the content directory.
    """)
    template = MetadataDefault("template", default="page.html", doc="""
        Template used to render the page. Defaults to `page.html`, although specific
        pages of some features can default to other template names.

        Use this similarly to [Jekill's layouts](https://jekyllrb.com/docs/step-by-step/04-layouts/).
    """)
    site_url = MetadataInherited("site_url", doc="""
        Base URL for the site, used to generate an absolute URL to the page.
    """)
    site_path = Metadata("site_path", doc="""
        Where a content directory appears in the site.

        By default, is is the `site_path` of the parent directory, plus the directory
        name.

        If you are publishing the site at `/prefix` instead of the root of the domain,
        override this with `/prefix` in the content root.
    """)
    author = MetadataInherited("author", doc="""
        A string with the name of the author for this page.

        SITE_AUTHOR is used as a default if found in settings.

        If not found, it defaults to the current user's name.
    """)

    date = MetadataDate("date", doc="""
        Publication date for the page.

        A python datetime object, timezone aware. If the date is in the future when
        `ssite` runs, the page will be consider a draft and will be ignored. Use `ssite
        --draft` to also consider draft pages.

        If missing, the modification time of the file is used.
    """)

    copyright = MetadataTemplateInherited("copyright", template="template_copyright", doc="""
        If `template_copyright` is set instead of `copyright`, it is a jinja2 template
        used to generate the copyright information.

        The template context will have `page` available, with the current page. The
        result of the template will not be further escaped, so you can use HTML markup
        in it.

        If missing, defaults to `"© {{meta.date.year}} {{meta.author}}"`
    """)

    title = MetadataTemplateInherited("title", template="template_title", doc="""
        The page title.

        If `template_title` is set instead of `title`, it is a jinja2 template used to
        generate the title. The template context will have `page` available, with the
        current page. The result of the template will not be further escaped, so you
        can use HTML markup
        in it.

        If omitted:

         * the first title found in the page contents is used.
         * in the case of jinaj2 template pages, the contents of `{% block title %}`,
           if present, is rendered and used.
         * if the page has no title, the title of directory indices above this page is
           inherited.
         * if still no title can be found, the site name is used as a default.
    """)

    description = MetadataTemplateInherited("description", template="template_description", doc="""
        The page description. If omitted, the page will have no description.

        If `template_description` is set instead of `description`, it is a jinja2
        template used to generate the description. The template context will have
        `page` available, with the current page. The result of the template will not be
        further escaped, so you can use HTML markup in it.
    """)

    asset = MetadataInherited("asset", doc="""
        If set to True for a file (for example, by a `file:` pattern in a directory
        index), the file is loaded as a static asset, regardless of whether a feature
        would load it.

        If set to True in a directory index, the directory and all its subdirectories
        are loaded as static assets, without the interventions of features.
    """)

    indexed = MetadataIndexed("indexed", doc="""
        If true, the page appears in [directory indices](dir.md) and in
        [page filter results](page_filter.md).

        It defaults to true at least for [Markdown](markdown.md),
        [reStructuredText](rst.rst), and [data](data.md) pages.
    """)

    draft = MetadataDraft("draft", doc="""
If true, the page is still a draft and will not appear in the destination site,
unless draft mode is enabled.

It defaults to false, or true if `meta.date` is in the future.
""")


class MetaMixin:
    """
    Functionality to expose a `meta` member giving dict-like access to Metadata
    fields
    """
    def create_meta(
            self,
            site: Site, parent: Optional[MetaMixin],
            meta_values: Optional[dict[str, Any]] = None) -> Meta:
        if parent is None:
            self.meta = Meta(site.metadata)
        else:
            self.meta = parent.meta.derive()
        if meta_values is not None:
            self.meta.update(meta_values)
        # TODO: update with _fields
        for field in self._fields.values():
            field.fill_new(self, parent)

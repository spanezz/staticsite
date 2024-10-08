from __future__ import annotations

import io
import logging
import os
import re
from collections import defaultdict
from collections.abc import Sequence
from typing import IO, TYPE_CHECKING, Any

import jinja2

from staticsite import fields
from staticsite.archetypes import Archetype
from staticsite.feature import Feature, PageTrackingMixin, TrackedField
from staticsite.features.jinja2 import RenderPartialTemplateMixin
from staticsite.page import Page, SourcePage, TemplatePage
from staticsite.page_filter import PageFilter
from staticsite.utils import yaml_codec

if TYPE_CHECKING:
    from staticsite import file, fstree
    from staticsite.archetypes import Archetypes
    from staticsite.site import Site
    from staticsite.source_node import SourcePageNode

log = logging.getLogger("data")


re_ext = re.compile(r"\.(json|toml|yaml)$")


class DataTypeField(TrackedField["DataPageMixin", str], fields.Str["DataPageMixin"]):
    """
    Type of data for this file.

    Identifies the data type. Internally, the data feature groups data pages by
    type, so further features can efficiently access thematic datasets.

    This is used to group data of the same type together, and to choose a
    `data-[data_type].html` rendering template.

    The `page.meta.template` metadata for data pages, when not specified, defaults
    to `dir-[type].html`, or if that is missing, to `data.html`.
    """

    tracked_by = "data"


class DataPageMixin(Page):
    data_type = DataTypeField()


class DataPages(PageTrackingMixin["DataPageMixin"], Feature):
    """
    Handle datasets in content directories.

    This allows storing pure-data datasets in JSON, Yaml, or Toml format in
    the contents directory, access it from pages, and render it using Jinja2
    templates.

    Each dataset needs, at its toplevel, to be a dict with a ``type`` element,
    and the dataset will be rendered using the ``data-{{type}}.html`` template.

    Other front-matter attributes like ``date``, ``title``, ``aliases``, and
    taxonomy names are handled as with other pages. The rest of the dictionary
    is ignored and can contain any data one wants.
    """

    def __init__(self, *args: Any, **kw: Any):
        super().__init__(*args, **kw)
        self.by_type: dict[str, list[Page]] = defaultdict(list)
        self.j2_globals["data_pages"] = self.jinja2_data_pages
        self.page_class_by_type: dict[str, type[Page]] = {}

    def get_page_bases(self, page_cls: type[Page]) -> Sequence[type[Page]]:
        return (DataPageMixin,)

    def register_page_class(self, type: str, cls: type[Page]) -> None:
        self.page_class_by_type[type] = cls

    def get_used_page_types(self) -> list[type[Page]]:
        return [DataPage]

    def load_dir(
        self,
        node: SourcePageNode,
        directory: fstree.Tree,
        files: dict[str, tuple[dict[str, Any], file.File]],
    ) -> list[Page]:
        taken: list[str] = []
        pages: list[Page] = []
        for fname, (kwargs, src) in files.items():
            mo = re_ext.search(fname)
            if not mo:
                continue
            taken.append(fname)

            fmt = mo.group(1)

            with directory.open(fname, "rt") as fd:
                try:
                    fm_meta = parse_data(fd, fmt)
                except Exception:
                    log.exception("%s: failed to parse %s content", src.relpath, fmt)
                    continue

            try:
                data_type = fm_meta.get("data_type", None)
            except AttributeError:
                log.error("%s: data did not parse into a dict", src.relpath)
                continue

            if data_type is None:
                log.error("%s: data_type not found: ignoring page", src.relpath)
                continue

            page_name = fname[: -len(mo.group(0))]
            kwargs.update(fm_meta)
            kwargs["page_cls"] = self.page_class_by_type.get(data_type, DataPage)
            kwargs["src"] = src

            if page_name == "index":
                page = node.create_source_page_as_index(**kwargs)
            else:
                page = node.create_source_page_as_path(name=page_name, **kwargs)
            if page is not None:
                pages.append(page)

        for fname in taken:
            del files[fname]

        return pages

    def try_load_archetype(
        self, archetypes: Archetypes, relpath: str, name: str
    ) -> Archetype | None:
        mo = re_ext.search(relpath)
        if not mo:
            return None
        fmt = mo.group(1)
        if os.path.basename(relpath) != name + "." + fmt:
            return None
        return DataArchetype(archetypes, relpath, self, fmt)

    def organize(self) -> None:
        # Dispatch pages by type
        for page in self.tracked_pages:
            data_type = page.data_type
            if data_type is None:
                continue
            self.by_type[data_type].append(page)

        # Sort the pages of each type by date
        for pages in self.by_type.values():
            pages.sort(key=lambda x: x.date)

    @jinja2.pass_context
    def jinja2_data_pages(
        self,
        context: jinja2.runtime.Context,
        type: str,
        path: str | None = None,
        limit: int | None = None,
        sort: str | None = None,
        **kw: str,
    ) -> list[Page]:
        page_filter = PageFilter(
            self.site,
            path=path,
            limit=limit,
            sort=sort,
            allow=self.by_type.get(type, []),
            root=None,
            **kw,
        )
        return page_filter.filter()


def parse_data(fd: IO[str], fmt: str) -> Any:
    if fmt == "json":
        import json

        return json.load(fd)
    elif fmt == "toml":
        import toml

        return toml.load(fd)
    elif fmt == "yaml":
        return yaml_codec.load(fd)
    else:
        raise NotImplementedError(f"data format {fmt} is not supported")


def write_data(fd: IO[str], data: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        import json

        json.dump(data, fd)
    elif fmt == "toml":
        import toml

        toml.dump(data, fd)
    elif fmt == "yaml":
        yaml_codec.dump(data, fd)
    else:
        raise NotImplementedError(f"data format {fmt} is not supported")


class DataPage(RenderPartialTemplateMixin, TemplatePage, SourcePage):
    """
    Data files

    Data files have a `.json`, `.yaml`, or `.toml` extension and can be rendered
    with custom Jinja2 templates.

    The content of the data file is parsed, and merged into the page metadata.

    The jinja2 template can be chosen using the `data_type` metadata field.

    The metadata of any page with the `data_type` metadata will be also tracked as
    data. This allows to create normal pages that also add to a named dataset.
    """

    TYPE = "data"

    def __init__(self, site: Site, **kw: Any):
        # Indexed by default
        kw.setdefault("indexed", True)
        if "template" not in kw:
            kw["template"] = site.theme.jinja2.select_template(
                [f"data-{kw['data_type']}.html", "data.html"]
            )
        super().__init__(site, **kw)


class DataArchetype(Archetype):
    def __init__(
        self, archetypes: Archetypes, relpath: str, data_pages: DataPages, fmt: str
    ):
        super().__init__(archetypes, relpath)
        self.data_pages = data_pages
        self.format = fmt

    def render(self, **kw: Any) -> tuple[dict[str, Any], str]:
        meta, rendered = super().render(**kw)

        # Reparse the rendered version
        with io.StringIO(rendered) as fd:
            data = parse_data(fd, self.format)

        # Make a copy of the full parsed metadata
        archetype_meta = dict(data)

        # Remove the path entry
        data.pop("path", None)

        # Reserialize the data
        with io.StringIO() as fd:
            write_data(fd, data, self.format)
            post_body = fd.getvalue()

        return archetype_meta, post_body


FEATURES = {
    "data": DataPages,
}

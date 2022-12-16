from __future__ import annotations

import io
import logging
import os
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import jinja2

from staticsite import fields
from staticsite.archetypes import Archetype
from staticsite.feature import Feature
from staticsite.features.jinja2 import RenderPartialTemplateMixin
from staticsite.node import Node, Path
from staticsite.page import SourcePage, Page
from staticsite.page_filter import PageFilter
from staticsite.utils import yaml_codec

if TYPE_CHECKING:
    from staticsite import file, scan

log = logging.getLogger("data")


re_ext = re.compile(r"\.(json|toml|yaml)$")


class DataPageMixin(metaclass=fields.FieldsMetaclass):
    data_type = fields.Field(doc="""
        Type of data for this file.

        This is used to group data of the same type together, and to choose a
        `data-[data_type].html` rendering template.
    """)


class DataPages(Feature):
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
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.by_type = defaultdict(list)
        self.j2_globals["data_pages"] = self.jinja2_data_pages
        self.page_class_by_type = {}
        self.page_mixins.append(DataPageMixin)
        self.site.features.add_tracked_metadata("data_type")

    def register_page_class(self, type: str, cls):
        self.page_class_by_type[type] = cls

    def load_dir(
            self,
            node: Node,
            directory: scan.Directory,
            files: dict[str, tuple[dict[str, Any], file.File]]) -> list[Page]:
        taken = []
        pages = []
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

            page_name = fname[:-len(mo.group(0))]
            kwargs.update(fm_meta)

            if (directory_index := page_name == "index"):
                path = Path()
            else:
                path = Path((page_name,))

            page = node.create_source_page(
                page_cls=self.page_class_by_type.get(data_type, DataPage),
                src=src,
                directory_index=directory_index,
                path=path,
                **kwargs)
            pages.append(page)

        for fname in taken:
            del files[fname]

        return pages

    def try_load_archetype(self, archetypes, relpath, name):
        mo = re_ext.search(relpath)
        if not mo:
            return None
        fmt = mo.group(1)
        if os.path.basename(relpath) != name + "." + fmt:
            return None
        return DataArchetype(archetypes, relpath, self, fmt)

    def organize(self):
        # Dispatch pages by type
        for page in self.site.features.pages_by_metadata["data_type"]:
            data_type = page.data_type
            self.by_type[data_type].append(page)

        # Sort the pages of each type by date
        for pages in self.by_type.values():
            pages.sort(key=lambda x: x.date)

    @jinja2.pass_context
    def jinja2_data_pages(self, context, type, path=None, limit=None, sort=None, **kw):
        page_filter = PageFilter(self.site, path=path, limit=limit, sort=sort, allow=self.by_type.get(type, []), **kw)
        return page_filter.filter()


def parse_data(fd, fmt):
    if fmt == "json":
        import json
        return json.load(fd)
    elif fmt == "toml":
        import toml
        return toml.load(fd)
    elif fmt == "yaml":
        return yaml_codec.load(fd)
    else:
        raise NotImplementedError("data format {} is not supported".format(fmt))


def write_data(fd, data, fmt):
    if fmt == "json":
        import json
        json.dump(data, fd)
    elif fmt == "toml":
        import toml
        toml.dump(data, fd)
    elif fmt == "yaml":
        yaml_codec.dump(data, fd)
    else:
        raise NotImplementedError("data format {} is not supported".format(fmt))


class DataPage(RenderPartialTemplateMixin, SourcePage):
    TYPE = "data"

    def __init__(self, site, **kw):
        # Indexed by default
        kw.setdefault("indexed", True)
        if "template" not in kw:
            kw["template"] = site.theme.jinja2.select_template(
                    [f"data-{kw['data_type']}.html", "data.html"])
        super().__init__(site, **kw)


class DataArchetype(Archetype):
    def __init__(self, archetypes, relpath, data_pages, fmt):
        super().__init__(archetypes, relpath)
        self.data_pages = data_pages
        self.format = fmt

    def render(self, **kw):
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

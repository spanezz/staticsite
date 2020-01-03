from __future__ import annotations
from typing import TYPE_CHECKING, List
from staticsite import Page, Feature
from staticsite.archetypes import Archetype
from staticsite.utils import yaml_codec
from staticsite.page_filter import PageFilter
from staticsite.metadata import Metadata
import jinja2
import re
import os
import io
from collections import defaultdict
import logging

if TYPE_CHECKING:
    from staticsite.contents import ContentDir

log = logging.getLogger("data")


re_ext = re.compile(r"\.(json|toml|yaml)$")


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
        self.site.tracked_metadata.add("data_type")

        self.site.register_metadata(Metadata("data_type", doc="""
Type of data for this file.

This is used to group data of the same type together, and to choose a
`data-[data_type].html` rendering template.
"""))

    def register_page_class(self, type: str, cls):
        self.page_class_by_type[type] = cls

    def load_dir(self, sitedir: ContentDir) -> List[Page]:
        taken = []
        pages = []
        for fname, src in sitedir.files.items():
            mo = re_ext.search(fname)
            if not mo:
                continue
            taken.append(fname)

            meta = sitedir.meta_file(fname)

            fmt = mo.group(1)

            with sitedir.open(fname, src, "rt") as fd:
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
            if page_name != "index":
                meta["site_path"] = os.path.join(sitedir.meta["site_path"], page_name)
            else:
                meta["site_path"] = sitedir.meta["site_path"]

            meta.update(fm_meta)

            cls = self.page_class_by_type.get(data_type, DataPage)
            page = cls(self.site, src, meta=meta, dir=sitedir)
            pages.append(page)

        for fname in taken:
            del sitedir.files[fname]

        return pages

    def try_load_archetype(self, archetypes, relpath, name):
        mo = re_ext.search(relpath)
        if not mo:
            return None
        fmt = mo.group(1)
        if os.path.basename(relpath) != name + "." + fmt:
            return None
        return DataArchetype(archetypes, relpath, self, fmt)

    def finalize(self):
        # Dispatch pages by type
        for page in self.site.pages_by_metadata["data_type"]:
            data_type = page.meta.get("data_type")
            self.by_type[data_type].append(page)

        # Sort the pages of each type by date
        for pages in self.by_type.values():
            pages.sort(key=lambda x: x.meta["date"])

    @jinja2.contextfunction
    def jinja2_data_pages(self, context, type, path=None, limit=None, sort=None, **kw):
        page_filter = PageFilter(self.site, path=path, limit=limit, sort=sort, **kw)
        return page_filter.filter(self.by_type.get(type, []))


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


class DataPage(Page):
    TYPE = "data"

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.meta["build_path"] = os.path.join(self.meta["site_path"], "index.html")

        # Indexed by default
        self.meta.setdefault("indexed", True)

        if "template" not in self.meta:
            self.meta["template"] = self.site.theme.jinja2.select_template(
                    [f"data-{self.meta['data_type']}.html", "data.html"])


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

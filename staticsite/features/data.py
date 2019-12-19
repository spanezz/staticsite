from __future__ import annotations
from typing import List
from staticsite import Page, Feature
from staticsite.archetypes import Archetype
from staticsite.utils import yaml_codec
from staticsite.contents import ContentDir
import dateutil.parser
import jinja2
import re
import os
import io
import datetime
from collections import defaultdict
import logging

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
    RUN_BEFORE = ["contents_loaded"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.by_type = defaultdict(list)
        self.j2_globals["data_pages"] = self.jinja2_data_pages
        self.page_class_by_type = {}

    def register_page_class(self, type: str, cls):
        self.page_class_by_type[type] = cls

    def load_dir(self, sitedir: ContentDir) -> List[Page]:
        # meta = sitedir.meta_features.get("md")
        # if meta is None:
        #     meta = {}

        taken = []
        pages = []
        for fname, src in sitedir.files.items():
            mo = re_ext.search(fname)
            if not mo:
                continue

            data = load_data(src, mo.group(1))
            if data is None:
                continue

            try:
                type = data.get("type", None)
            except AttributeError:
                log.error("%s: data did not parse into a dict", src.relpath)
                continue

            if type is None:
                log.error("%s: data type not found: ignoring page", src.relpath)
                continue

            cls = self.page_class_by_type.get(type, DataPage)
            page = cls(self.site, src, data, meta=sitedir.meta_file(fname))
            if not page.is_valid():
                continue

            data_type = page.meta.get("type")
            self.by_type[data_type].append(page)

            taken.append(fname)
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
        for type, pages in self.by_type.items():
            pages.sort(key=lambda x: x.meta["date"])

    @jinja2.contextfunction
    def jinja2_data_pages(self, context, type, path=None, limit=None, sort=None, **kw):
        from .theme import PageFilter
        page_filter = PageFilter(self.site, path=path, limit=limit, sort=sort, **kw)
        return page_filter.filter(self.by_type.get(type, []))


def load_data(src, fmt):
    with open(src.abspath, "rt") as fd:
        try:
            return parse_data(fd, fmt)
        except Exception:
            log.exception("%s: failed to parse %s content", src.relpath, fmt)
            return


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

    def __init__(self, site, src, data, meta=None):
        dirname, basename = os.path.split(src.relpath)
        if basename.startswith("index.") or basename.startswith("README."):
            linkpath = dirname
        else:
            linkpath = os.path.splitext(src.relpath)[0]
        super().__init__(
            site=site,
            src=src,
            src_linkpath=linkpath,
            dst_relpath=os.path.join(linkpath, "index.html"),
            dst_link=os.path.join(site.settings.SITE_ROOT, linkpath),
            meta=meta)

        # Indexed by default
        self.meta.setdefault("indexed", True)

        # Read and parse the contents
        if self.src.stat is None:
            if self.meta.get("date", None) is None:
                self.meta["date"] = self.site.generation_time
        else:
            if self.meta.get("date", None) is None:
                self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)

        self.meta.update(data)
        self.data = data

        date = self.meta.get("date", None)
        if date is not None and not isinstance(date, datetime.datetime):
            self.meta["date"] = dateutil.parser.parse(date)

        if "template" not in self.meta:
            self.meta["template"] = self.site.theme.jinja2.select_template(
                    [f"data-{self.meta['type']}.html", "data.html"])

    def to_dict(self):
        from staticsite.utils import dump_meta
        res = super().to_dict()
        res["data"] = dump_meta(self.data)
        return res


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

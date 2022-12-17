from __future__ import annotations

import inspect
import logging
import os
from typing import TYPE_CHECKING, Type
from . import asset
from . import dirindex

if TYPE_CHECKING:
    from . import fields
    from .site import Site
    from .feature import Feature
    from .page import Page

log = logging.getLogger("autodoc")


class Autodoc:
    """
    Autogenerate reference documentation
    """
    def __init__(self, site: Site, root: str):
        self.site = site
        self.root = root

    def generate(self):
        # Iterate features to generate per-feature documentation
        page_types: set[Type[Page]] = {asset.Asset, dirindex.Dir}
        for feature in self.site.features.ordered():
            self.write_feature(feature)
            page_types.update(feature.get_used_page_types())

        # Iterate page types
        by_name: dict[str, Type[Page]] = {}
        for base_page_type in page_types:
            page_type = self.site.features.get_page_class(base_page_type)
            name = page_type.TYPE
            if (old := by_name.get(name)) is not None:
                raise RuntimeError(f"Page type {name} defined as both {old} and {page_type}")
            else:
                by_name[name] = page_type
        for name, page_type in by_name.items():
            self.write_page_type(name, page_type)

        # TODO: iterate page types to generate per-page documentation
        # TODO: document fields in per-page documentation, or link to per-field
        #       documentation

        # - Have features populate a directory of markdown files, one per feature
        #    - Have features iterate on their supported pages, documenting them
        #      and their fields
        # - update self-generated metadata fields documentation
        #    - generate documentation for the various kinds of pages
        #    - lift __doc__ from pages, or another attribute gathered from all mixins
        #      by the metaclass, or by the documenter by following the MRO, for more
        #      documentation content

    def write_feature(self, feature: Feature):
        path = os.path.join(self.root, "features")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, f"{feature.name}.md"), "wt") as out:
            out.write(inspect.cleandoc(feature.__doc__))

    def write_page_type(self, name: str, page_type: Type[Page]):
        if page_type.__doc__ is None:
            log.error("%s: page type is undocumented in %s", name, page_type)
            return
        path = os.path.join(self.root, "pages")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, f"{name}.md"), "wt") as out:
            out.write(inspect.cleandoc(page_type.__doc__))

    def write_field(self, name: str, field: fields.Field):
        raise NotImplementedError()

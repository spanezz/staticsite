from __future__ import annotations

import inspect
import logging
import os
from typing import TYPE_CHECKING, Any

from . import asset

if TYPE_CHECKING:
    from .feature import Feature
    from .fields import Field
    from .page import Page
    from .site import Site

log = logging.getLogger("autodoc")


def summary(obj: Any) -> str:
    if obj.__doc__ is None:
        return f"Missing documentation for {obj!r}"
    return inspect.cleandoc(obj.__doc__).strip().split("\n\n", 1)[0]


def body(obj: Any) -> str:
    if obj.__doc__ is None:
        return f"Missing documentation for {obj!r}"
    res = inspect.cleandoc(obj.__doc__).strip().split("\n\n", 1)
    if len(res) == 2:
        return res[1]
    else:
        return res[0]


class Autodoc:
    """
    Autogenerate reference documentation
    """

    def __init__(self, site: Site, root: str):
        self.site = site
        self.root = root

    def generate(self) -> None:
        # Iterate features to generate per-feature documentation
        page_types: set[type[Page]] = {asset.Asset}
        for feature in self.site.features.ordered():
            self.write_feature(feature)
            page_types.update(feature.get_used_page_types())

        # Iterate page types
        by_name: dict[str, type[Page]] = {}
        for base_page_type in page_types:
            page_type = self.site.features.get_page_class(base_page_type)
            name = page_type.TYPE
            if (old := by_name.get(name)) is not None:
                raise RuntimeError(
                    f"Page type {name} defined as both {old} and {page_type}"
                )
            else:
                by_name[name] = page_type
        fields: dict[str, Field[Any, Any]] = {}
        for name, page_type in by_name.items():
            self.write_page_type(name, page_type)
            fields.update(page_type._fields)

        # Iterate fields
        for name, field in fields.items():
            self.write_field(name, field)

        # Generate index
        with open(os.path.join(self.root, "README.md"), "wt") as out:
            print("# Reference documentation", file=out)
            print(file=out)
            print("## Core structure", file=out)
            print(file=out)
            print("* [The Site object](site.md)", file=out)
            # print("* [The Page object](page.md)", file=out)
            print("* [Site settings](settings.md)", file=out)
            print("* [Source contents](contents.md)", file=out)
            print("* [Themes](theme.md)", file=out)
            # print("* [Jinja2 templates reference](templates.md)", file=out)
            print("* [Selecting site pages](page-filter.md)", file=out)
            print("* [Archetypes reference](archetypes.md)", file=out)
            print("* [Site-specific features](feature.md)", file=out)
            print("* [Front Matter](front-matter.md)", file=out)
            print(file=out)

            print("## Features", file=out)
            print(file=out)
            for feature in sorted(self.site.features.ordered(), key=lambda f: f.name):
                print(
                    f"* [{feature.name}](features/{feature.name}.md): {summary(feature)}",
                    file=out,
                )
            print(file=out)

            print("## Page types", file=out)
            print(file=out)
            for name, page_type in sorted(by_name.items()):
                print(f"* [{name}](pages/{name}.md): {summary(page_type)}", file=out)
            print(file=out)

            print("## Page fields", file=out)
            print(file=out)
            for name, field in sorted(fields.items()):
                print(f"* [{name}](fields/{name}.md): {summary(field)}", file=out)
            print(file=out)
            print("[Back to README](../../README.md)", file=out)

        # - update self-generated metadata fields documentation
        #    - generate documentation for the various kinds of pages
        #    - lift __doc__ from pages, or another attribute gathered from all mixins
        #      by the metaclass, or by the documenter by following the MRO, for more
        #      documentation content

    def write_feature(self, feature: Feature) -> None:
        page_types = feature.get_used_page_types()
        path = os.path.join(self.root, "features")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, f"{feature.name}.md"), "wt") as out:
            print(f"# {feature.name}: {summary(feature)}", file=out)
            print(file=out)

            if page_types:
                print("## Page types", file=out)
                print(file=out)
                for page_type in page_types:
                    print(
                        f"* [{page_type.TYPE}](../pages/{page_type.TYPE}.md): {summary(page_type)}",
                        file=out,
                    )
                print(file=out)

            print("## Documentation", file=out)
            print(file=out)
            print(body(feature), file=out)
            print(file=out)
            print("[Back to reference index](../README.md)", file=out)

    def write_page_type(self, name: str, page_type: type[Page]) -> None:
        if page_type.__doc__ is None:
            log.error("%s: page type is undocumented in %s", name, page_type)
            return
        path = os.path.join(self.root, "pages")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, f"{name}.md"), "wt") as out:
            print(f"# {name}: {summary(page_type)}", file=out)
            print(file=out)
            print("## Fields", file=out)
            print(file=out)
            for name, field in sorted(page_type._fields.items()):
                print(f"* [{name}](../fields/{name}.md): {summary(field)}", file=out)
            print(file=out)
            print("## Documentation", file=out)
            print(file=out)
            print(body(page_type), file=out)
            print(file=out)
            print("[Back to reference index](../README.md)", file=out)

    def write_field(self, name: str, field: Field[Any, Any]) -> None:
        path = os.path.join(self.root, "fields")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, f"{name}.md"), "wt") as out:
            print(f"# {name}: {summary(field)}", file=out)
            print(file=out)
            print(body(field), file=out)
            print(file=out)
            print("[Back to reference index](../README.md)", file=out)

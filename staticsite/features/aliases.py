from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from staticsite import fields
from staticsite.feature import Feature, PageTrackingMixin, TrackedField
from staticsite.page import AutoPage, ChangeExtent, Page, SourcePage, TemplatePage
from staticsite.site import Path

if TYPE_CHECKING:
    from staticsite.features import rst

log = logging.getLogger("aliases")


class AliasField(TrackedField[Page, list[str]]):
    """
    Relative paths in the destination directory where the page should also show up.
    [Like in Hugo](https://gohugo.io/extras/aliases/), this can be used to maintain
    existing links when moving a page to a different location.
    """

    tracked_by = "aliases"

    def _clean(self, page: Page, value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            return value
        elif isinstance(value, tuple):
            return list(value)
        else:
            raise TypeError(
                f"invalid value of type {type(value)} for {page!r}.{self.name}:"
                " expecting, str, list[str], or tuple[str]"
            )


class SourcePageField(fields.Field["AliasPage", SourcePage]):
    """
    Field containing a SourcePage
    """

    def _clean(self, page: AliasPage, value: Any) -> SourcePage:
        if isinstance(value, SourcePage):
            return value
        else:
            raise TypeError(
                f"invalid value of type {type(value)} for {page!r}.{self.name}:"
                " expecting, SourcePage"
            )


class AliasesPageMixin(Page):
    aliases = AliasField(structure=True)


class AliasesFeature(PageTrackingMixin[AliasesPageMixin], Feature):
    """
    Build redirection pages for page aliases.

    A page can define 'aliases=[...]' to generate pages in those locations that
    redirect to the page.
    """

    RUN_AFTER = ["rst"]

    def __init__(self, *args: Any, **kw: Any):
        super().__init__(*args, **kw)
        cast("rst.RestructuredText", self.site.features["rst"]).yaml_tags.add("aliases")

    def get_page_bases(self, page_cls: type[Page]) -> Sequence[type[Page]]:
        return (AliasesPageMixin,)

    def get_used_page_types(self) -> list[type[Page]]:
        return [AliasPage]

    def generate(self) -> None:
        # Build alias pages from pages with an 'aliases' metadata
        for page in self.tracked_pages:
            if not (aliases := page.aliases):
                continue

            for alias in aliases:
                path = Path.from_string(alias)
                node = self.site.root.generate_path(path.dir)
                if old := node.lookup_page(Path((path.name,))):
                    if old == page:
                        log.warning(
                            "%r defines alias %r pointing to itself", page, alias
                        )
                    else:
                        log.warning(
                            "%r defines alias %r pointing to existing page %r",
                            page,
                            alias,
                            old,
                        )
                    continue
                node.create_auto_page_as_path(
                    page_cls=AliasPage,
                    created_from=page,
                    page=page,
                    title=page.title,
                    name=path.name,
                )


class AliasPage(TemplatePage, AutoPage):
    """
    Page rendering a redirect to another page
    """

    page = SourcePageField(doc="Page this alias redirects to")
    TYPE = "alias"
    TEMPLATE = "redirect.html"

    def _compute_change_extent(self) -> ChangeExtent:
        if self.created_from is None:
            raise AssertionError(f"AliasPage {self!r} has empty created_from")
        res = self.created_from.change_extent
        if res == ChangeExtent.CONTENTS:
            res = ChangeExtent.UNCHANGED
        return res


FEATURES = {
    "aliases": AliasesFeature,
}

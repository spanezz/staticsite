from __future__ import annotations

import logging
from typing import Sequence, Type

from staticsite import fields
from staticsite.feature import Feature, PageTrackingMixin, TrackedField
from staticsite.node import Path
from staticsite.page import (AutoPage, ChangeExtent, Page, SourcePage,
                             TemplatePage)

log = logging.getLogger("aliases")


class AliasField(TrackedField[Page, list[str]]):
    """
    Relative paths in the destination directory where the page should also show up.
    [Like in Hugo](https://gohugo.io/extras/aliases/), this can be used to maintain
    existing links when moving a page to a different location.
    """
    tracked_by = "aliases"


class AliasesPageMixin(Page):
    aliases = AliasField(structure=True)


class AliasesFeature(PageTrackingMixin, Feature):
    """
    Build redirection pages for page aliases.

    A page can define 'aliases=[...]' to generate pages in those locations that
    redirect to the page.
    """
    RUN_AFTER = ["rst"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site.features["rst"].yaml_tags.add("aliases")

    def get_page_bases(self, page_cls: Type[Page]) -> Sequence[Type[Page]]:
        return (AliasesPageMixin,)

    def generate(self):
        # Build alias pages from pages with an 'aliases' metadata
        for page in self.tracked_pages:
            if not (aliases := page.aliases):
                continue

            for alias in aliases:
                path = Path.from_string(alias)
                node = self.site.root.generate_path(path.dir)
                if (old := node.lookup_page(Path((path.name,)))):
                    if old == page:
                        log.warning("%r defines alias %r pointing to itself", page, alias)
                    else:
                        log.warning("%r defines alias %r pointing to existing page %r", page, alias, old)
                    continue
                node.create_auto_page_as_path(
                        page_cls=AliasPage,
                        created_from=page,
                        page=page,
                        title=page.title,
                        name=path.name)


class AliasPage(TemplatePage, AutoPage):
    """
    Page rendering a redirect to another page
    """
    page = fields.Field["AliasPage", SourcePage](doc="Page this alias redirects to")
    TYPE = "alias"
    TEMPLATE = "redirect.html"

    def _compute_change_extent(self) -> ChangeExtent:
        res = self.created_from.change_extent
        if res == ChangeExtent.CONTENTS:
            res = ChangeExtent.UNCHANGED
        return res


FEATURES = {
    "aliases": AliasesFeature,
}

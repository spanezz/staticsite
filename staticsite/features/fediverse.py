from __future__ import annotations

import logging
from collections.abc import Sequence

from staticsite import fields
from staticsite.feature import Feature
from staticsite.page import Page

log = logging.getLogger("aliases")


class FediversePageMixin(Page):
    fediverse_id: fields.Str[Page] = fields.Str()


class FediverseFeature(Feature):
    """
    Track a fediverse ID for a page.
    """

    def get_page_bases(self, page_cls: type[Page]) -> Sequence[type[Page]]:
        return (FediversePageMixin,)

    def get_used_page_types(self) -> list[type[Page]]:
        return [FediversePageMixin]


FEATURES = {
    "fediverse": FediverseFeature,
}

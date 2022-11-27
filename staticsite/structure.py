from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .site import Site
    from .page import Page


class Structure:
    def __init__(self, site: Site):
        # Site pages that have the given metadata
        self.pages_by_metadata: dict[str, list[Page]] = defaultdict(list)

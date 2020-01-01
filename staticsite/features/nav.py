from __future__ import annotations
from staticsite.feature import Feature
from staticsite.metadata import Metadata
import logging

log = logging.getLogger("nav")


class Nav(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site.register_metadata(Metadata("nav", inherited=True, structure=True, doc=f"""
List of page paths that are used for the navbar
"""))


FEATURES = {
    "nav": Nav,
}

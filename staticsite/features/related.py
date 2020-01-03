from __future__ import annotations
from staticsite.feature import Feature
from staticsite import metadata
import logging

log = logging.getLogger("related")


class RelatedFeature(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    RUN_AFTER = ["autogenerated_pages"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.site.register_metadata(metadata.Metadata("related", structure=True, doc="""
Dict of pages related to this page.

Dict values will be resolved as pages.

If there are no related pages, `page.meta.related` will be guaranteed to exist
as an empty dictionary.

Features can add to this. For example, [syndication](syndication.md) can add
`meta.related.archive`, `meta.related.rss`, and `meta.related.atom`.
"""))

    def finalize(self):
        # Expand pages expressions
        for page in self.site.pages.values():
            related = page.meta.get("related", None)
            if related is None:
                page.meta[self.name] = related = {}

            for k, v in related.items():
                if isinstance(v, str):
                    related[k] = page.resolve_path(v)


FEATURES = {
    "related": RelatedFeature,
}
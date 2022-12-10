from __future__ import annotations

import logging

from staticsite import fields
from staticsite.feature import Feature

log = logging.getLogger("related")


class RelatedPageMixin(metaclass=fields.FieldsMetaclass):
    related = fields.Field(structure=True, doc="""
        Dict of pages related to this page.

        Dict values will be resolved as pages.

        If there are no related pages, `page.meta.related` will be guaranteed to exist
        as an empty dictionary.

        Features can add to this. For example, [syndication](syndication.md) can add
        `meta.related.archive`, `meta.related.rss`, and `meta.related.atom`.
    """)


class RelatedFeature(Feature):
    """
    Expand a 'pages' metadata containing a page filter into a list of pages.
    """
    RUN_AFTER = ["autogenerated_pages"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.page_mixins.append(RelatedPageMixin)

    def organize(self):
        # Expand pages expressions
        # TODO: redo this using a tracked metadata
        for page in self.site.iter_pages(static=False):
            if (related := page.related) is None:
                related = {}
                setattr(page, self.name, related)

            for k, v in related.items():
                if isinstance(v, str):
                    related[k] = page.resolve_path(v)


FEATURES = {
    "related": RelatedFeature,
}

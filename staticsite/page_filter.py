from .utils import compile_page_match


class PageFilter:
    """
    Engine for selecting pages in the site
    """

    def __init__(self, site, path=None, limit=None, sort=None, **kw):
        self.site = site

        if path is not None:
            self.re_path = compile_page_match(path)
        else:
            self.re_path = None

        self.sort = sort
        if sort is not None:
            if sort.startswith("-"):
                self.sort = sort[1:]
                self.sort_reverse = True
            else:
                self.sort_reverse = False

        self.taxonomy_filters = []
        for taxonomy in self.site.features["tags"].taxonomies.values():
            t_filter = kw.get(taxonomy.name)
            if t_filter is None:
                continue
            self.taxonomy_filters.append((taxonomy.name, frozenset(t_filter)))

        self.limit = limit

    def filter(self, all_pages):
        pages = []

        for page in all_pages:
            if not page.FINDABLE:
                continue
            if self.re_path is not None and not self.re_path.match(page.src.relpath):
                continue
            if self.sort is not None and self.sort != "url" and self.sort not in page.meta:
                continue
            fail_taxonomies = False
            for name, t_filter in self.taxonomy_filters:
                page_tags = frozenset(t.name for t in page.meta.get(name, ()))
                if not t_filter.issubset(page_tags):
                    fail_taxonomies = True
            if fail_taxonomies:
                    continue
            pages.append(page)

        if self.sort is not None:
            if self.sort == "url":
                def sort_by(p):
                    return p.dst_link
            else:
                def sort_by(p):
                    return p.meta.get(self.sort, None)
            pages.sort(key=sort_by, reverse=self.sort_reverse)

        if self.limit is not None:
            pages = pages[:self.limit]

        return pages

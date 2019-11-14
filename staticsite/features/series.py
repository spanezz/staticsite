from staticsite.feature import Feature
import logging

log = logging.getLogger()


class SeriesFeature(Feature):
    RUN_AFTER = ["taxonomies"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.for_metadata.append("series")
        self.series = {}

    def finalize(self):
        taxonomies = self.site.features["taxonomies"].taxonomies
        # Auto-create series from taxonomies
        for taxonomy in taxonomies:
            for name in taxonomy.meta.get("series_tags", ()):
                for page in taxonomy.items[name].pages:
                    self.add_page_to_series(page, name)

        # Finalize series
        for series in self.series.values():
            series.finalize()

    def add_page(self, page):
        series_name = page.meta.get("series", None)
        if series_name is None:
            return
        self.add_page_to_series(page, series_name)

    def add_page_to_series(self, page, series_name):
        existing_series = page.meta.get("series")
        if existing_series is not None and existing_series != series_name:
            # Only add the page to the first series found.
            # To break ambiguity with multiple series-tags, explicitly specify
            # series= in pages
            return

        series = self.series.get(series_name, None)
        if series is None:
            self.series[series_name] = series = Series(series_name)

        page.meta["series"] = series_name
        series.add_page(page)


class Series:
    def __init__(self, name):
        self.name = name
        self.pages = []

    def add_page(self, page):
        if page not in self.pages:
            self.pages.append(page)

    def finalize(self):
        self.pages.sort(key=lambda p: p.meta["date"])

        first = self.pages[0]
        last = self.pages[-1]

        series_title = None
        for idx in range(len(self.pages)):
            cur = self.pages[idx]

            # Assign series_prev and series_next metadata elements to pages
            cur.meta["series_index"] = idx + 1
            cur.meta["series_length"] = len(self.pages)
            cur.meta["series_first"] = first
            cur.meta["series_last"] = last
            cur.meta["series_prev"] = self.pages[idx - 1] if idx > 0 else None
            cur.meta["series_next"] = self.pages[idx + 1] if idx < len(self.pages) - 1 else None

            # Assign series-title as the title of the first page in the series, or
            # the value of the last set series_title metadata set in a page
            if "series_title" in cur.meta:
                series_title = cur.meta["series_title"]
            else:
                if series_title is None:
                    series_title = cur.meta.get("title", self.name)
                cur.meta["series_title"] = series_title

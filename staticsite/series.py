import logging

log = logging.getLogger()

class Series:
    def __init__(self, name):
        self.name = name
        self.pages = []

    def add_page(self, page):
        self.pages.append(page)

    def finalize(self):
        self.pages.sort(key=lambda p: p.meta["date"])

        first = self.pages[0]
        last = self.pages[-1]

        series_title = None
        for idx in range(len(self.pages)):
            cur = self.pages[idx]

            # Assign series_prev and series_next metadata elements to pages
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

import logging

log = logging.getLogger()

class Series:
    def __init__(self):
        self.pages = []

    def add_page(self, page):
        self.pages.append(page)

    def finalize(self):
        pass

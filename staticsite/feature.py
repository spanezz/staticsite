from typing import Optional, Dict, Callable
from .page import Page
from . import site


class Feature:
    def __init__(self, site: "site.Site"):
        self.site = site
        self.j2_globals: Dict[str, Callable] = {}
        self.j2_filters: Dict[str, Callable] = {}

    def try_load_page(self, root_abspath: str, relpath: str) -> Optional[Page]:
        """
        Try loading a page from the given path.

        Returns None if this path is not handled by this Feature
        """
        return None

    def finalize(self):
        """
        Hook called after all the pages have been loaded
        """
        pass

from typing import Optional, Dict, Callable
from .page import Page
from . import site


class Feature:
    def __init__(self, site: "site.Site"):
        self.site = site
        # Feature-provided jinja2 globals
        self.j2_globals: Dict[str, Callable] = {}
        # Feature-provided jinja2 filters
        self.j2_filters: Dict[str, Callable] = {}
        # Names of page.meta elements that are relevant to this feature
        self.for_metadata = []

    def add_page(self, page):
        """
        Add a page to this series, when it contains one of the metadata items
        defined in for_metadata
        """
        raise NotImplementedError("Feature.add_page")

    def try_load_page(self, root_abspath: str, relpath: str) -> Optional[Page]:
        """
        Try loading a page from the given path.

        Returns None if this path is not handled by this Feature
        """
        return None

    def build_test_page(self, **kw) -> Page:
        """
        Build a test page
        """
        raise NotImplementedError

    def finalize(self):
        """
        Hook called after all the pages have been loaded
        """
        pass

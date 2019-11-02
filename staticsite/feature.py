from typing import Optional
from .page import Page


class Feature:
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

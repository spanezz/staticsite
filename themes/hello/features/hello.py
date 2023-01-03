from __future__ import annotations

from typing import Any

import jinja2

from staticsite.cmd.site import FeatureCommand
from staticsite.feature import Feature


class Hello(Feature):
    """
    Example custom feature for staticsite.

    It:
    * adds a hello metadata element to all pages that do not have it already
    * adds a hello() function to jinja2 that fetches the contents of their hello
      element
    """
    def __init__(self, *args: Any, **kw: Any):
        super().__init__(*args, **kw)
        self.j2_globals["hello"] = self.hello

    @jinja2.contextfunction
    def hello(self, context: jinja2.runtime.Context):
        # This function, called from a jinja2 template, has access to the
        # render context. staticsite puts 'page' in the render context,
        # pointing to the Page object being rendered.
        return context.page.meta.get("hello", "oddly, no hello here")

    def organize(self):
        # Add a 'hello' metadata element to all pages
        # This runs after 'taxonomies' and 'dirs', so it also annotates the
        # pages they generate
        for page in self.site.iter_pages(static=False):
            page.meta.setdefault("hello", "Hello " + page.meta.get("title", "page"))

    def add_site_commands(self, subparsers):
        # Add an example command as ssite site --cmd hello
        super().add_site_commands(subparsers)
        HelloCmd.add_subparser(subparsers)


class HelloCmd(FeatureCommand):
    "greet the user"

    NAME = "hello"

    def run(self) -> None:
        count = 0
        for page in self.site.iter_pages(static=False):
            count += 1
        print(f"Hello from {self.site.settings.SITE_NAME}!")
        print(f"I contain {count} pages.")


#  FEATURES dict defines which features are activated and with which name.
FEATURES = {
    "hello": Hello,
}

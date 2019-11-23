from staticsite.feature import Feature
from staticsite.cmd.site import FeatureCommand
import jinja2


class Hello(Feature):
    """
    Example custom feature for staticsite.

    It:
    * adds a hello metadata element to all pages that do not have it already
    * adds a hello() function to jinja2 that fetches the contents of their hello
      element
    """
    RUN_AFTER = ["tags", "dirs"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.j2_globals["hello"] = self.hello

    @jinja2.contextfunction
    def hello(self, context):
        # This function, called from a jinja2 template, has access to the
        # render context. staticsite puts 'page' in the render context,
        # pointing to the Page object being rendered.
        return context.page.meta.get("hello", "oddly, no hello here")

    def finalize(self):
        # Add a 'hello' metadata element to all pages
        # This runs after 'taxonomies' and 'dirs', so it also annotates the
        # pages they generate
        for page in self.site.pages.values():
            page.meta.setdefault("hello", "Hello " + page.meta.get("title", "page"))

    def add_site_commands(self, subparsers):
        # Add an example command as ssite site --cmd hello
        super().add_site_commands(subparsers)
        HelloCmd.make_subparser(subparsers)


class HelloCmd(FeatureCommand):
    "greet the user"

    NAME = "hello"

    def run(self):
        print(f"Hello from {self.site.settings.SITE_NAME}!")
        print("I contain {} pages.".format(len(self.site.pages)))


#  FEATURES dict defines which features are activated and with which name.
FEATURES = {
    "hello": Hello,
}
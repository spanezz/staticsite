#!/usr/bin/python3

import timeit
from staticsite import Site, Settings


def setup():
    settings = Settings()
    settings.PROJECT_ROOT = "example"
    settings.load("example/settings.py")
    site = Site(settings)
    site.features.load_default_features()
    site.load_theme()
    # Patch add_page to be a noop
    site.add_page = lambda page: None
    return site


# val = timeit.timeit("site.load_content_new()", setup="site = setup()\nsite.load_content_new()", number=300, globals=globals())
# print(f"New: {val}")

val = timeit.timeit("site.load_content()", setup="site = setup()\nsite.load_content()", number=300, globals=globals())
print(f"Current: {val}")

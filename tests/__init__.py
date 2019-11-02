# coding: utf-8
import os
from staticsite.page import Page
from staticsite.taxonomy import TaxonomyPage
from contextlib import contextmanager


def datafile_abspath(relpath):
    test_root = os.path.dirname(__file__)
    return os.path.join(test_root, "data", relpath)


@contextmanager
def example_site():
    import tempfile
    import shutil
    src = os.path.join(os.getcwd(), "example")
    with tempfile.TemporaryDirectory() as root:
        dst = os.path.join(root, "site")
        shutil.copytree(src, dst)
        yield dst


class TestArgs:
    def __init__(self, **kw):
        self._args = kw

    def __getattr__(self, k):
        return self._args.get(k, None)


class TestPage(Page):
    TYPE = "test"
    FINDABLE = True

    def __init__(self, site, relpath, **meta):
        super().__init__(
            site=site,
            root_abspath="/",
            src_relpath=relpath,
            src_linkpath=relpath,
            dst_relpath=relpath,
            dst_link=relpath)
        self._future_meta = meta

    def read_metadata(self):
        self.meta.update(**self._future_meta)
        super().read_metadata()


class TestTaxonomyPage(TaxonomyPage):
    def __init__(self, site, name, meta={}):
        self._future_meta = meta
        super().__init__(site, "/tmp/", name + ".taxonomy")

    def _read_taxonomy_description(self):
        self.meta.update(**self._future_meta)

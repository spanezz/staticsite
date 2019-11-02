import pytz
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
        if "date" in meta and meta["date"].tzinfo is None:
            meta["date"] = meta["date"].replace(tzinfo=pytz.utc)

        super().__init__(
            site=site,
            root_abspath="/",
            src_relpath=relpath,
            src_linkpath=relpath,
            dst_relpath=relpath,
            dst_link=relpath)
        self.meta.update(**meta)

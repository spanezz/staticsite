from __future__ import annotations
from typing import Dict, Union
import os
import tempfile
from contextlib import contextmanager
import pytz
import staticsite
from staticsite.settings import Settings
from staticsite.utils import write_front_matter


class TestSettings(Settings):
    def __init__(self, **kw):
        kw.setdefault("CACHE_REBUILDS", False)
        kw.setdefault("THEME", datafile_abspath("theme"))
        super().__init__()
        for k, v in kw.items():
            setattr(self, k, v)


class Site(staticsite.Site):
    def __init__(self, **kw):
        settings = TestSettings(**kw)
        super().__init__(settings=settings)

    def load_without_content(self):
        self.features.load_default_features()
        self.load_theme()


def datafile_abspath(relpath):
    test_root = os.path.dirname(__file__)
    return os.path.join(test_root, "data", relpath)


@contextmanager
def workdir(files: Dict[str, Union[str, bytes, Dict]] = None):
    """
    Create a temporary directory and populate it with the given files
    """
    if files is None:
        files = {}
    with tempfile.TemporaryDirectory() as root:
        for relpath, content in files.items():
            abspath = os.path.join(root, relpath)
            os.makedirs(os.path.dirname(abspath), exist_ok=True)
            if isinstance(content, str):
                with open(abspath, "wt") as fd:
                    fd.write(content)
            elif isinstance(content, bytes):
                with open(abspath, "wb") as fd:
                    fd.write(content)
            elif isinstance(content, dict):
                with open(abspath, "wt") as fd:
                    fd.write(write_front_matter(content, style="json"))
            else:
                raise TypeError("content should be a str or bytes")
        yield root


@contextmanager
def example_site():
    import shutil
    src = os.path.join(os.getcwd(), "example")
    with tempfile.TemporaryDirectory() as root:
        dst = os.path.join(root, "site")
        shutil.copytree(src, dst)
        yield dst


class Args:
    """
    Mock argparser namespace initialized with options from constructor
    """
    def __init__(self, **kw):
        self._args = kw

    def __getattr__(self, k):
        return self._args.get(k, None)


class Page(staticsite.Page):
    TYPE = "test"
    FINDABLE = True

    def __init__(self, site, relpath, **meta):
        if "date" in meta and meta["date"].tzinfo is None:
            meta["date"] = meta["date"].replace(tzinfo=pytz.utc)

        super().__init__(
            site=site,
            src=staticsite.File(relpath, root="/", abspath="/" + relpath),
            src_linkpath=relpath,
            dst_relpath=relpath,
            dst_link=relpath)
        self.meta.update(**meta)

from __future__ import annotations
from typing import Dict, Union
import os
import tempfile
import logging
from contextlib import contextmanager
import staticsite
from staticsite.settings import Settings
from staticsite.utils import front_matter


class TestSettings(Settings):
    def __init__(self, **kw):
        kw.setdefault("CACHE_REBUILDS", False)
        kw.setdefault("THEME", datafile_abspath("theme"))
        super().__init__()
        for k, v in kw.items():
            setattr(self, k, v)


class Site(staticsite.Site):
    def __init__(self, **kw):
        kw.setdefault("SITE_NAME", "Test site")
        kw.setdefault("SITE_URL", "https://www.example.org")
        settings = TestSettings(**kw)
        super().__init__(settings=settings)

    def load_without_content(self):
        self.features.load_default_features()
        self.load_theme()
        self.theme.load_assets()


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
                    fd.write(front_matter.write(content, style="json"))
            else:
                raise TypeError("content should be a str or bytes")
        yield root


@contextmanager
def example_site():
    """
    Create a copy of the example site in a temporary directory
    """
    import shutil
    src = os.path.join(os.getcwd(), "example")
    with tempfile.TemporaryDirectory() as root:
        dst = os.path.join(root, "site")
        shutil.copytree(src, dst)
        yield dst


class TracebackHandler(logging.Handler):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.collected = []

    def handle(self, record):
        import traceback
        if record.stack_info is None:
            record.stack_info = traceback.print_stack()
        self.collected.append(record)


@contextmanager
def assert_no_logs(level=logging.WARN):
    handler = TracebackHandler(level=level)
    try:
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        yield
    finally:
        root_logger.removeHandler(handler)
    if handler.collected:
        raise AssertionError(f"{len(handler.collected)} unexpected loggings")


class Args:
    """
    Mock argparser namespace initialized with options from constructor
    """
    def __init__(self, **kw):
        self._args = kw

    def __getattr__(self, k):
        return self._args.get(k, None)

from __future__ import annotations
from typing import Dict, Union
import os
import tempfile
import logging
from contextlib import contextmanager
import staticsite
from staticsite.settings import Settings
from staticsite.utils import front_matter


class Site(staticsite.Site):
    def __init__(self, taxonomies=(), **kw):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        kw.setdefault("SITE_NAME", "Test site")
        kw.setdefault("SITE_URL", "https://www.example.org")
        kw.setdefault("SITE_AUTHOR", "Test User")
        kw.setdefault("CACHE_REBUILDS", False)
        kw.setdefault("THEME_PATHS", [os.path.join(project_root, "themes")])
        settings = Settings()
        for k, v in kw.items():
            setattr(settings, k, v)
        super().__init__(settings=settings)
        self._taxonomies = taxonomies


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
def testsite(files: Dict[str, Union[str, bytes, Dict]] = None, **kw):
    """
    Take a dict representing directory contents and build a Site for it
    """
    with workdir(files) as root:
        site = Site(CONTENT=root, **kw)
        site.load()
        site.analyze()
        yield site


@contextmanager
def example_site_dir(name="demo"):
    """
    Create a copy of the example site in a temporary directory
    """
    import shutil
    src = os.path.join(os.getcwd(), "example", name)
    with tempfile.TemporaryDirectory() as root:
        dst = os.path.join(root, "site")
        shutil.copytree(src, dst)
        yield dst


@contextmanager
def example_site(name="demo", **kw):
    with assert_no_logs():
        with example_site_dir(name) as root:
            src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            settings = Settings()
            settings_path = os.path.join(root, "settings.py")
            if os.path.exists(settings_path):
                settings.load(settings_path)
            if settings.PROJECT_ROOT is None:
                settings.PROJECT_ROOT = root
            settings.CACHE_REBUILDS = False
            settings.THEME_PATH = [os.path.join(src_root, "themes")]
            for k, v in kw.items():
                setattr(settings, k, v)

            site = staticsite.Site(settings=settings)
            site.load()
            site.analyze()
            yield site


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

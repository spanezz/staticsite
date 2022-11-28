from __future__ import annotations
from typing import Dict, Union, Any
import os
import stat
import tempfile
import logging
import datetime
import pytz
from contextlib import contextmanager
import staticsite
from staticsite.settings import Settings
from staticsite.utils import front_matter
from unittest import mock


@contextmanager
def mock_file_stat(overrides: Dict[int, Any]):
    """
    Override File.stat contents.

    Overrides is a dict like: `{"st_mtime": 12345}`
    """
    real_stat = os.stat
    real_file_from_dir_entry = staticsite.File.from_dir_entry

    # See https://www.peterbe.com/plog/mocking-os.stat-in-python
    def mock_stat(*args, **kw):
        res = list(real_stat(*args, **kw))
        for k, v in overrides.items():
            res[getattr(stat, k.upper())] = v
        return os.stat_result(res)

    def mock_file_from_dir_entry(dir, entry):
        res = real_file_from_dir_entry(dir, entry)
        st = list(res.stat)
        for k, v in overrides.items():
            st[getattr(stat, k.upper())] = v
        res = staticsite.File(res.relpath, res.abspath, os.stat_result(st))
        return res

    with mock.patch("staticsite.file.os.stat", new=mock_stat):
        with mock.patch("staticsite.file.File.from_dir_entry", new=mock_file_from_dir_entry):
            yield


class StatOverride:
    """
    Override file stat() results with well-known values
    """
    def __init__(self, kw):
        """
        Pluck the arguments we need from a bundle of keyword arguments
        """
        self.stat_override = kw.pop("stat_override", None)
        if self.stat_override is None:
            self.stat_override = {
                # date +%s --date="2019-06-01 12:30"
                "st_mtime": 1559385000,
            }
        elif self.stat_override is False:
            self.stat_override = None

        self.generation_time = kw.pop("generation_time", None)
        if self.generation_time is None:
            self.generation_time = datetime.datetime(2020, 2, 1, 16, 0, tzinfo=pytz.utc)
        elif self.generation_time is False:
            self.generation_time = None

    @contextmanager
    def __call__(self, site):
        if self.generation_time is not None:
            site.generation_time = self.generation_time
        with mock_file_stat(self.stat_override):
            yield


def test_settings(**kw):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    kw.setdefault("SITE_NAME", "Test site")
    kw.setdefault("SITE_URL", "https://www.example.org")
    kw.setdefault("SITE_AUTHOR", "Test User")
    kw.setdefault("TIMEZONE", "Europe/Rome")
    kw.setdefault("CACHE_REBUILDS", False)
    kw.setdefault("THEME_PATHS", [os.path.join(project_root, "themes")])

    settings = Settings()
    for k, v in kw.items():
        setattr(settings, k, v)
    return settings


class Site(staticsite.Site):
    def __init__(self, taxonomies=(), **kw):
        settings = test_settings(**kw)
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
    stat_override = StatOverride(kw)

    with workdir(files) as root:
        settings = test_settings(PROJECT_ROOT=root, **kw)
        site = staticsite.Site(settings)
        with stat_override(site):
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
    stat_override = StatOverride(kw)

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
            settings.THEME_PATHS = [os.path.join(src_root, "themes")]
            for k, v in kw.items():
                setattr(settings, k, v)
            if settings.TIMEZONE is None:
                settings.TIMEZONE = "Europe/Rome"
            if settings.SITE_URL is None:
                settings.SITE_URL = "http://localhost"
            if settings.SITE_NAME is None:
                settings.SITE_NAME = "Test Site"

            site = staticsite.Site(settings=settings)
            with stat_override(site):
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

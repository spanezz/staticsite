from __future__ import annotations

import contextlib
import datetime
import logging
import os
import stat
import tempfile
from contextlib import contextmanager
from typing import Any, Dict, Optional, Sequence, Union
from unittest import TestCase, mock

import pytz

import staticsite
from staticsite.settings import Settings
from staticsite.utils import front_matter

MockFiles = dict[str, Union[str, bytes, dict]]

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class MockSite:
    """
    Define a mock site for testing
    """
    def __init__(self, files: MockFiles):
        self.files = files
        self.site: Optional[staticsite.Site] = None
        self.stack = contextlib.ExitStack()
        self.root: Optional[str] = None
        self.test_case: Optional[TestCase] = None

        # Timestamp used for mock files and site generation time
        # date +%s --date="2019-06-01 12:30"
        self.generation_time = 1559385000

        self.settings = Settings()
        # Default settings for testing
        self.settings.SITE_NAME = "Test site"
        self.settings.SITE_URL = "https://www.example.org"
        self.settings.SITE_AUTHOR = "Test User"
        self.settings.TIMEZONE = "Europe/Rome"
        self.settings.CACHE_REBUILDS = False
        self.settings.THEME_PATHS = [os.path.join(project_root, "themes")]

    def populate_workdir(self):
        self.root = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.settings.PROJECT_ROOT = self.root

        for relpath, content in self.files.items():
            abspath = os.path.join(self.root, relpath)
            os.makedirs(os.path.dirname(abspath), exist_ok=True)
            if isinstance(content, str):
                with open(abspath, "wt") as fd:
                    fd.write(content)
                    os.utime(fd.fileno(), (self.generation_time, self.generation_time))
            elif isinstance(content, bytes):
                with open(abspath, "wb") as fd:
                    fd.write(content)
                    os.utime(fd.fileno(), (self.generation_time, self.generation_time))
            elif isinstance(content, dict):
                with open(abspath, "wt") as fd:
                    fd.write(front_matter.write(content, style="json"))
                    os.utime(fd.fileno(), (self.generation_time, self.generation_time))
            else:
                raise TypeError("content should be a str or bytes")

    def __enter__(self) -> "MockSite":
        self.populate_workdir()
        self.site = staticsite.Site(
                self.settings,
                generation_time=datetime.datetime.fromtimestamp(self.generation_time, pytz.utc))
        self.site.load()
        self.site.analyze()
        return self

    def __exit__(self, *args):
        self.site = None
        self.stack.__exit__(*args)

    def page(self, *paths: tuple[str]) -> tuple[staticsite.Page]:
        """
        Ensure the site has the given page, by path, and return it
        """
        res: list[staticsite.Page] = []
        for path in paths:
            page = self.site.find_page(path)
            if page is None:
                self.test_case.fail(f"Page {path!r} not found in site")
            res.append(page)
        if len(res) == 1:
            return res[0]
        else:
            return tuple(res)

    def assertPagePaths(self, paths: Sequence[str]):
        """
        Check that the list of pages in the site matches the given paths
        """
        self.test_case.assertCountEqual([p.site_path for p in self.site.iter_pages(static=False)], paths)


class MockSiteTestMixin:
    @contextmanager
    def site(self, mocksite: Union[MockSite, MockFiles]):
        if not isinstance(mocksite, MockSite):
            mocksite = MockSite(mocksite)
        mocksite.test_case = self
        with mocksite:
            yield mocksite


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
def example_site_dir(name="demo") -> str:
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
def example_site(name="demo", **kw) -> staticsite.Site:
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


class SiteTestMixin:
    site_name: str
    site_settings: dict[str, Any] = {}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from staticsite.cmd.build import Builder

        cls.build_root_tmpdir = tempfile.TemporaryDirectory()
        cls.build_root = cls.build_root_tmpdir.__enter__()

        cls.example_site = example_site(name=cls.site_name, **cls.site_settings)
        cls.site = cls.example_site.__enter__()
        cls.site.settings.OUTPUT = cls.build_root

        builder = Builder(cls.site)
        builder.write()
        cls.build_root = builder.build_root
        cls.build_log = builder.build_log

    @classmethod
    def tearDownClass(cls):
        cls.example_site.__exit__(None, None, None)
        cls.build_root_tmpdir.__exit__(None, None, None)
        super().tearDownClass()

    def assertBuilt(self, srcpath: str, sitepath: str, dstpath: str, sample: Union[str, bytes, None] = None):
        page = self.site.find_page(sitepath)
        self.assertEqual(page.src.relpath, srcpath)

        rendered = self.build_log.get(dstpath)
        if rendered is None:
            for path, pg in self.build_log.items():
                if pg == page:
                    self.fail(f"{dstpath!r} not found in render log; {srcpath!r} was rendered as {path!r} instead")
                    break
            else:
                self.fail(f"{dstpath!r} not found in render log")

        if rendered != page:
            for path, pg in self.build_log.items():
                if pg == page:
                    self.fail(f"{dstpath!r} rendered {rendered!r} instead of {page!r}."
                              " {srcpath!r} was rendered as {path!r} instead")
                    break
            else:
                self.fail(f"{dstpath!r} rendered {rendered!r} instead of {page!r}")

        if os.path.isdir(os.path.join(self.build_root, dstpath)):
            self.fail(f"{dstpath!r} rendered as a directory")

        if sample is not None:
            if isinstance(sample, bytes):
                args = {"mode": "rb"}
            else:
                args = {"mode": "rt", "encoding": "utf-8"}
            with open(os.path.join(self.build_root, dstpath), **args) as fd:
                if sample not in fd.read():
                    self.fail(f"{dstpath!r} does not contain {sample!r}")

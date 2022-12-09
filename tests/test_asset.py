from __future__ import annotations

import datetime
import os
import time
from contextlib import contextmanager
from unittest import TestCase

import pytz

from staticsite.file import File
from staticsite.site import Site

from . import utils as test_utils


@contextmanager
def override_tz(val):
    orig = os.environ.get("TZ", None)
    os.environ["TZ"] = val
    time.tzset()
    yield
    if orig is None:
        del os.environ["TZ"]
    else:
        os.environ["TZ"] = orig
    time.tzset()


class TestAsset(test_utils.MockSiteTestMixin, TestCase):
    @test_utils.assert_no_logs()
    @override_tz("Pacific/Samoa")
    def test_timestamps(self):
        # $ TZ=UTC date +%s --date="2016-11-01" → 1477958400
        FILE_TS = 1477958400

        sitedef = test_utils.MockSite({
            ".staticsite": {
                "asset": True,
            },
            "testasset": "test",
        })
        sitedef.auto_load_site = False
        sitedef.mock_file_mtime = None

        with self.site(sitedef) as mocksite:
            # Set file mtime and check that it can be read back correctly
            path = os.path.join(mocksite.root, "testasset")
            os.utime(path, (FILE_TS, FILE_TS))
            src = File.with_stat("testasset", path)
            self.assertEqual(src.stat.st_mtime, FILE_TS)

            # Load site contents
            mocksite.load_site(until=Site.LOAD_STEP_CONTENTS)

            page = mocksite.page("testasset")

            self.assertEqual(page.node.name, "")
            self.assertEqual(page.TYPE, "asset")
            self.assertEqual(page.src.stat.st_mtime, FILE_TS)
            self.assertEqual(page.meta["date"], datetime.datetime(2016, 11, 1, 0, 0, 0, tzinfo=pytz.utc))
            self.assertEqual(page.meta["site_url"], "https://www.example.org")
            self.assertEqual(page.site_path, "testasset")
            self.assertEqual(page.build_path, "testasset")
            self.assertFalse(page.directory_index)

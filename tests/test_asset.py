from __future__ import annotations

import datetime
import os
import tempfile
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
        with self.site({}, auto_load_site=False) as mocksite:
            mocksite.load_site(until=Site.LOAD_STEP_CONTENTS)
            with tempfile.NamedTemporaryFile() as f:
                # $ TZ=UTC date +%s --date="2016-11-01" → 1477958400
                os.utime(f.name, (1477958400, 1477958400))
                src = File(os.path.basename(f.name), abspath=f.name, stat=os.stat(f.name))
                page = mocksite.site.root.add_asset(src=src, name="testasset")

                self.assertEqual(page.meta["date"], datetime.datetime(2016, 11, 1, 0, 0, 0, tzinfo=pytz.utc))
                self.assertEqual(page.meta["site_url"], "https://www.example.org")
                self.assertEqual(page.site_path, "testasset")
                self.assertEqual(page.build_path, "testasset")
                self.assertFalse(page.directory_index)

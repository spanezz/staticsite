from unittest import TestCase
from . import utils as test_utils
from staticsite.asset import Asset
from staticsite.file import File
from contextlib import contextmanager
import os
import time
import tempfile
import datetime
import pytz


@contextmanager
def override_env(**kw):
    orig = {k: os.environ[k] for k in kw}
    for k, v in kw.items():
        os.environ[k] = v
    yield
    for k, v in orig.items():
        os.environ[k] = v


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


class TestAsset(TestCase):
    @test_utils.assert_no_logs()
    def test_timestamps(self):
        site = test_utils.Site()
        site.load_without_content()

        with override_tz("Pacific/Samoa"):
            with tempfile.NamedTemporaryFile() as f:
                # $ TZ=UTC date +%s --date="2016-11-01" → 1477958400
                os.utime(f.name, (1477958400, 1477958400))
                src = File(os.path.basename(f.name), abspath=f.name, stat=os.stat(f.name))
                page = Asset(site, src, meta={"site_path": src.relpath})

                self.assertEqual(page.meta["date"], datetime.datetime(2016, 11, 1, 0, 0, 0, tzinfo=pytz.utc))

# coding: utf-8
from unittest import TestCase
from staticsite.site import Site
from staticsite.asset import Asset
from contextlib import contextmanager
import os
import time
import tempfile
import datetime
import pytz

@contextmanager
def override_env(**kw):
    orig = { k: os.environ[k] for k in kw }
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


class TestSite(TestCase):
    def test_timestamps(self):
        site = Site()

        with override_tz("Pacific/Samoa"):
            with tempfile.NamedTemporaryFile() as f:
                # $ TZ=UTC date +%s --date="2016-11-01" → 1477958400
                os.utime(f.name, (1477958400, 1477958400))

                page = Asset(site, os.path.dirname(f.name), os.path.basename(f.name))

                self.assertEqual(page.meta["date"], datetime.datetime(2016, 11, 1, 0, 0, 0, tzinfo=pytz.utc))

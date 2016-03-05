from unittest import TestCase
from staticsite.core import Settings
from staticsite import global_settings
from . import datafile_abspath
import os

class TestSettings(TestCase):
    def test_defaults(self):
        s = Settings()
        self.assertEquals(s.TIMEZONE, global_settings.TIMEZONE)

    def test_as_dict(self):
        s = Settings()
        d = s.as_dict()
        self.assertEquals(d["TIMEZONE"], global_settings.TIMEZONE)

    def test_add_module(self):
        s = Settings()
        self.assertFalse(hasattr(s, "PRIO_USER"))

        s.add_module(os)

        # Merging a module add all uppercase symbols
        self.assertEquals(s.PRIO_USER, os.PRIO_USER)

        # And ignores all lowercase ones
        self.assertFalse(hasattr(s, "getuid"))

    def test_load(self):
        s = Settings()
        self.assertFalse(hasattr(s, "UPPERCASE"))

        s.load(datafile_abspath("settings.py"))

        self.assertEquals(s.UPPERCASE, True)
        self.assertFalse(hasattr(s, "lowercase"))
        self.assertFalse(hasattr(s, "os"))

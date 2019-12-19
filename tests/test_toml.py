from unittest import TestCase, SkipTest
from staticsite.utils import front_matter
import toml


toml_valid = """+++
date = "Tue, 24 Aug 2010 13:13:38 +0000"
tags = [ "valid" ]
bool = true
+++
"""

toml_invalid_bool = """+++
date = "Tue, 24 Aug 2010 13:13:38 +0000"
tags = [ "bug" ]
bool = True
+++
"""


class TestToml(TestCase):
    def test_valid(self):
        self.maxDiff = None
        fmt, data = front_matter.parse(toml_valid.splitlines())
        self.assertEqual(fmt, "toml")
        self.assertEqual(data, {
            "date": "Tue, 24 Aug 2010 13:13:38 +0000",
            "tags": ["valid"],
            "bool": True,
        })

    def test_invalid_bool(self):
        with self.assertRaises(toml.decoder.TomlDecodeError):
            fmt, data = front_matter.parse(toml_invalid_bool.splitlines())

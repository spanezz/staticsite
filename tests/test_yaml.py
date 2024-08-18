import io
from unittest import SkipTest, TestCase

from staticsite.utils import yaml_codec

yaml_sample = """---
key: val
bool: true
"""

yaml_sample_sorted = """---
bool: true
key: val
"""

yaml_sample_parsed = {
    "key": "val",
    "bool": True,
}


class YamlTestMixin:
    def test_loads(self):
        self.assertEqual(self.loads(self.sample), self.sample_parsed)
        self.assertEqual(self.loads(self.sample.encode()), self.sample_parsed)

    def test_load(self):
        with io.StringIO(self.sample) as fd:
            self.assertEqual(self.load(fd), self.sample_parsed)

    def test_dumps(self):
        self.assertEqual(self.dumps(self.sample_parsed), self.sample)

    def test_dump(self):
        with io.StringIO() as fd:
            self.dump(self.sample_parsed, fd)
            self.assertEqual(fd.getvalue(), self.sample)


class TestRuamel(YamlTestMixin, TestCase):
    def setUp(self):
        if yaml_codec.load_ruamel is None:
            raise SkipTest("ruamel.yaml not available")
        self.loads = yaml_codec.loads_ruamel
        self.load = yaml_codec.load_ruamel
        self.dumps = yaml_codec.dumps_ruamel
        self.dump = yaml_codec.dump_ruamel
        self.sample = yaml_sample
        self.sample_parsed = yaml_sample_parsed


class TestPyYAML(YamlTestMixin, TestCase):
    def setUp(self):
        if yaml_codec.load_pyyaml is None:
            raise SkipTest("PyYAML not available")
        self.loads = yaml_codec.loads_pyyaml
        self.load = yaml_codec.load_pyyaml
        self.dumps = yaml_codec.dumps_pyyaml
        self.dump = yaml_codec.dump_pyyaml
        self.sample = yaml_sample_sorted
        self.sample_parsed = yaml_sample_parsed

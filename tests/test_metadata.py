from unittest import TestCase
from . import utils as test_utils


class TestMetadata(TestCase):
    """
    Test metadata collected on site load
    """
    def test_asset(self):
        files = {
            ".staticsite": {
                "files": {
                    "test.md": {
                        "asset": True,
                    },
                },
            },
            "test.md": {},
            "test1.md": {},
        }

        with test_utils.workdir(files) as root:
            site = test_utils.Site()
            site.load(content_root=root)
            site.analyze()

            self.assertCountEqual(site.pages.keys(), [
                "", "test.md", "test1",
            ])

            index = site.pages[""]
            test = site.pages["test.md"]
            test1 = site.pages["test1"]

            self.assertEqual(index.TYPE, "dir")
            self.assertEqual(test.TYPE, "asset")
            self.assertEqual(test1.TYPE, "markdown")

from unittest import TestCase
from . import utils as test_utils


class TestDirs(TestCase):
    """
    Test dirs feature
    """
    def test_dirs(self):
        files = {
            "page_root.md": {},
            "dir1/page_sub.md": {},
            "dir1/dir2/dir3/page_sub3.md": {},
        }
        with test_utils.workdir(files) as root:
            site = test_utils.Site(CONTENT=root)
            site.load()
            site.analyze()

            # We have a root dir index and dir indices for all subdirs
            dir_root = site.pages["/"]
            dir_dir1 = site.pages["/dir1"]
            dir_dir2 = site.pages["/dir1/dir2"]
            dir_dir3 = site.pages["/dir1/dir2/dir3"]

            self.assertEqual(dir_root.TYPE, "dir")
            self.assertEqual(dir_dir1.TYPE, "dir")
            self.assertEqual(dir_dir3.TYPE, "dir")
            self.assertEqual(dir_dir3.TYPE, "dir")

            # Check the contents of all dirs
            self.assertCountEqual(dir_root.meta["pages"], [site.pages["/page_root"]])
            self.assertCountEqual(dir_root.subdirs, [dir_dir1])
            self.assertCountEqual(dir_dir1.meta["pages"], [site.pages["/dir1/page_sub"]])
            self.assertCountEqual(dir_dir1.subdirs, [dir_dir2])
            self.assertCountEqual(dir_dir2.meta["pages"], [])
            self.assertCountEqual(dir_dir2.subdirs, [dir_dir3])
            self.assertCountEqual(dir_dir3.meta["pages"], [site.pages["/dir1/dir2/dir3/page_sub3"]])
            self.assertCountEqual(dir_dir3.subdirs, [])

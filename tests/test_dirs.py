from unittest import TestCase

from . import utils as test_utils


class TestDirs(test_utils.MockSiteTestMixin, TestCase):
    """
    Test dirs feature
    """

    def test_dirs(self):
        files = {
            "page_root.md": {},
            "dir1/page_sub.md": {},
            "dir1/dir2/dir3/page_sub3.md": {},
            "dir1/dir2/dir3/page_sub3/slides.pdf": "",
            "dir1/dir2/dir3/page_sub4.md": {},
        }
        with self.site(files) as mocksite:
            # We have a root dir index and dir indices for all subdirs
            dir_root, dir_dir1, dir_dir2, dir_dir3 = mocksite.page(
                "", "dir1", "dir1/dir2", "dir1/dir2/dir3"
            )

            self.assertEqual(dir_root.TYPE, "dir")
            self.assertEqual(dir_dir1.TYPE, "dir")
            self.assertEqual(dir_dir3.TYPE, "dir")
            self.assertEqual(dir_dir3.TYPE, "dir")

            # Check the contents of all dirs
            self.assertCountEqual(dir_root.meta["pages"], [mocksite.page("page_root")])
            self.assertCountEqual(dir_root.subdirs, [dir_dir1])
            self.assertIsNone(dir_root.parent)
            self.assertEqual(dir_root.meta["title"], "Test site")
            self.assertEqual(dir_root.meta["template"], "dir.html")

            self.assertCountEqual(
                dir_dir1.meta["pages"], [mocksite.page("dir1/page_sub")]
            )
            self.assertCountEqual(dir_dir1.subdirs, [dir_dir2])
            self.assertEqual(dir_dir1.parent, dir_root)
            self.assertEqual(dir_dir1.meta["title"], "dir1")

            self.assertCountEqual(dir_dir2.meta["pages"], [])
            self.assertCountEqual(dir_dir2.subdirs, [dir_dir3])
            self.assertEqual(dir_dir2.parent, dir_dir1)
            self.assertEqual(dir_dir2.meta["title"], "dir2")

            self.assertCountEqual(
                dir_dir3.meta["pages"],
                [
                    mocksite.page("dir1/dir2/dir3/page_sub3"),
                    mocksite.page("dir1/dir2/dir3/page_sub4"),
                ],
            )
            self.assertCountEqual(dir_dir3.subdirs, [])
            self.assertEqual(dir_dir3.parent, dir_dir2)
            self.assertEqual(dir_dir3.meta["title"], "dir3")

            asset = mocksite.page("dir1/dir2/dir3/page_sub3/slides.pdf")
            self.assertEqual(asset.TYPE, "asset")

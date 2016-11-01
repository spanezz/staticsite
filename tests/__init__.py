# coding: utf-8
import os
from contextlib import contextmanager

def datafile_abspath(relpath):
    test_root = os.path.dirname(__file__)
    return os.path.join(test_root, "data", relpath)


@contextmanager
def example_site():
    import tempfile
    import shutil
    src = os.path.join(os.getcwd(), "example")
    with tempfile.TemporaryDirectory() as root:
        dst = os.path.join(root, "site")
        shutil.copytree(src, dst)
        yield dst


class TestArgs:
    def __init__(self, **kw):
        self._args = kw

    def __getattr__(self, k):
        return self._args.get(k, None)

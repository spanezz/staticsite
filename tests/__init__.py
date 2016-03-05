import os

def datafile_abspath(relpath):
    test_root = os.path.dirname(__file__)
    return os.path.join(test_root, "data", relpath)

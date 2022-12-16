from __future__ import annotations

import json
import os
from functools import cached_property

try:
    import lmdb
except ModuleNotFoundError:
    lmdb = None


if lmdb is not None:
    class Cache:
        def __init__(self, fname):
            self.fname = fname + ".lmdb"

        @cached_property
        def db(self):
            os.makedirs(os.path.dirname(self.fname), exist_ok=True)
            return lmdb.open(self.fname, metasync=False, sync=False, map_size=100*1024*1024)

        def get(self, relpath):
            with self.db.begin() as tr:
                res = tr.get(relpath.encode(), None)
                if res is None:
                    return None
                else:
                    return json.loads(res)

        def put(self, relpath, data):
            with self.db.begin(write=True) as tr:
                tr.put(relpath.encode(), json.dumps(data).encode())
else:
    import dbm

    class Cache:
        def __init__(self, fname):
            self.fname = fname

        @cached_property
        def db(self):
            os.makedirs(os.path.dirname(self.fname), exist_ok=True)
            return dbm.open(self.fname, "c")

        def get(self, relpath):
            res = self.db.get(relpath)
            if res is None:
                return None
            else:
                return json.loads(res)

        def put(self, relpath, data):
            self.db[relpath] = json.dumps(data)


class DisabledCache:
    """
    noop render cache, for when caching is disabled
    """
    def get(self, relpath):
        return None

    def put(self, relpath, data):
        pass


class Caches:
    """
    Repository of caches that, if kept across site builds, can speed up further
    builds
    """
    def __init__(self, root):
        self.root = root

    def get(self, name):
        return Cache(os.path.join(self.root, name))


class DisabledCaches:
    def get(self, name):
        return DisabledCache()

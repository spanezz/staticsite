from __future__ import annotations

import json
import os
from functools import cached_property
from typing import Any, Protocol, Type

try:
    import lmdb
    HAVE_LMDB = True
except ModuleNotFoundError:
    HAVE_LMDB = False


class Cache(Protocol):
    def __init__(self, fname: str):
        ...

    def get(self, relpath: str) -> Any:
        ...

    def put(self, relpath: str, data: Any) -> None:
        ...


CacheImplementation: Type[Cache]


if HAVE_LMDB:
    class LMDBCache:
        def __init__(self, fname: str):
            self.fname = fname + ".lmdb"

        @cached_property
        def db(self) -> lmdb.Environment:
            os.makedirs(os.path.dirname(self.fname), exist_ok=True)
            return lmdb.open(self.fname, metasync=False, sync=False, map_size=100*1024*1024)

        def get(self, relpath: str) -> Any:
            with self.db.begin() as tr:
                res = tr.get(relpath.encode(), None)
                if res is None:
                    return None
                else:
                    return json.loads(res)

        def put(self, relpath: str, data: Any) -> None:
            with self.db.begin(write=True) as tr:
                tr.put(relpath.encode(), json.dumps(data).encode())

    CacheImplementation = LMDBCache

else:
    import dbm

    class DBMCache:
        def __init__(self, fname: str):
            self.fname = fname

        # FIXME: using Any here because the dbm module is not typed
        @cached_property
        def db(self) -> Any:
            os.makedirs(os.path.dirname(self.fname), exist_ok=True)
            return dbm.open(self.fname, "c")

        def get(self, relpath: str) -> Any:
            res = self.db.get(relpath)
            if res is None:
                return None
            else:
                return json.loads(res)

        def put(self, relpath: str, data: Any) -> None:
            self.db[relpath] = json.dumps(data)

    CacheImplementation = DBMCache


class DisabledCache:
    """
    noop render cache, for when caching is disabled
    """
    def __init__(self, fname: str):
        self.fname = fname

    def get(self, relpath: str) -> Any:
        return None

    def put(self, relpath: str, data: Any) -> None:
        pass


class Caches:
    """
    Repository of caches that, if kept across site builds, can speed up further
    builds
    """
    def __init__(self, root: str):
        self.root = root

    def get(self, name: str) -> Cache:
        return CacheImplementation(os.path.join(self.root, name))


class DisabledCaches:
    def get(self, name: str) -> Cache:
        return DisabledCache(name)

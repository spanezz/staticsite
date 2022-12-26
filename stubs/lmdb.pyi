from __future__ import annotations

from typing import ContextManager


class Environment:
    def begin(self, db=None, parent=None, write=False, buffers=False) -> ContextManager[Transaction]:
        ...

    def get(self, key: str, default=None, db=None) -> bytes:
        ...

    def put(self, key: str, value: bytes, dupdata=True, overwrite=True, append=False, db=None):
        ...


class Transaction:
    ...


def open(
        path: str,
        map_size: int = 10485760,
        subdir: bool = True,
        readonly: bool = False,
        metasync: bool = True,
        sync: bool = True,
        map_async: bool = False,
        mode: int = 493,
        create: bool = True,
        readahead: bool = True,
        writemap: bool = False,
        meminit: bool = True,
        max_readers: int = 126,
        max_dbs: int = 0,
        max_spare_txns: int = 1,
        lock: bool = True) -> Environment:
    ...

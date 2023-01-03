from __future__ import annotations

from __future__ import annotations
from typing import ContextManager, Optional, TypeVar, Union, overload

T = TypeVar("T")


class _Database:
    ...


class Environment:
    def begin(
            self,
            db: Optional[_Database] = None,
            parent: Optional[Transaction] = None,
            write: bool = False,
            buffers: bool = False) -> ContextManager[Transaction]:
        ...

    @overload
    def get(self, key: bytes, default: bytes, db: Optional[_Database] = None) -> bytes:
        ...

    @overload
    def get(self, key: bytes, default: T, db: Optional[_Database] = None) -> Union[bytes, T]:
        ...

    def put(
            self,
            key: str, value: bytes,
            dupdata: bool = True,
            overwrite: bool = True,
            append: bool = False,
            db: Optional[_Database] = None) -> None:
        ...


class Transaction:
    @overload
    def get(self, key: bytes, default: bytes) -> bytes:
        ...

    @overload
    def get(self, key: bytes, default: T) -> Union[bytes, T]:
        ...

    def put(
            self,
            key: bytes, value: bytes,
            dupdata: bool = True,
            overwrite: bool = True,
            append: bool = False,
            db: Optional[_Database] = None) -> None:
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

from typing import Optional, Union

IN_CLOSE_WRITE: int
IN_DELETE: int


class WatchManager:
    def __init__(self) -> None:
        ...

    def add_watch(
            self, path: Union[str, list[str]], mask: int, proc_fun=None, rec: bool = False,
            auto_add: bool = False, do_glob: bool = False, quiet: bool = True,
            exclude_filter=None) -> dict[str, int]:
        ...

    def rm_watch(self, wd: Union[int, list[int]], rec: bool = False, quiet: bool = True) -> dict[int, bool]:
        ...


class Watch:
    ...


class AsyncioNotifier:
    def __init__(
            self, watch_manager: WatchManager, loop, callback=None,
            default_proc_fun=None, read_freq: int = 0, threshold: int = 0, timeout: Optional[int] = None):
        ...

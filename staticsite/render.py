from __future__ import annotations

import io
import os
import shutil

from .file import File


class RenderedElement:
    """
    Abstract interface for a rendered site page
    """
    def write(self, dst: File):
        """
        Write the rendered contents to the given file
        """
        raise NotImplementedError("{}.write", self.__class__.__name__)

    def content(self) -> bytes:
        """
        Return the rendered contents as bytes
        """
        raise NotImplementedError("{}.write", self.__class__.__name__)

    @classmethod
    def dirfd_open(cls, name, *args, dir_fd: int, **kw):
        """
        Open a file contained in the directory pointed to by dir_fd
        """
        def _file_opener(fname, flags):
            return os.open(fname, flags, mode=0o666, dir_fd=dir_fd)
        return io.open(name, *args, opener=_file_opener, **kw)


class RenderedFile(RenderedElement):
    def __init__(self, src: File):
        self.src = src

    def write(self, name: str, dir_fd: int):
        try:
            st = os.stat(name, dir_fd=dir_fd)
        except FileNotFoundError:
            st = None

        if st is None or (
                self.src.stat.st_mtime > st.st_mtime
                or self.src.stat.st_size != st.st_size):
            with open(self.src.abspath, "rb") as fd:
                with self.dirfd_open(name, "wb", dir_fd=dir_fd) as out:
                    shutil.copyfileobj(fd, out)
                    shutil.copystat(fd.fileno(), out.fileno())

    def content(self) -> bytes:
        with open(self.src.abspath, "rb") as fd:
            return fd.read()


class RenderedString(RenderedElement):
    def __init__(self, s):
        if s is None:
            self.buf = b"Error in page: see build logs"
        else:
            self.buf = s.encode("utf-8")

    def write(self, name: str, dir_fd: int):
        with self.dirfd_open(name, "wb", dir_fd=dir_fd) as out:
            out.write(self.buf)

    def content(self) -> bytes:
        return self.buf

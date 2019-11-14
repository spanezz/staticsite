from typing import NamedTuple, Optional
import shutil
import os


class FSFile(NamedTuple):
    """
    Information about a file in the file system.

    If stat is not None, the file exists and these are its stats.
    """
    path: str
    stat: Optional[os.stat_result] = None


class RenderedElement:
    """
    Abstract interface for a rendered site page
    """
    def write(self, dst: FSFile):
        """
        Write the rendered contents to the given file
        """
        raise NotImplementedError("{}.write", self.__class__.__name__)

    def content(self) -> bytes:
        """
        Return the rendered contents as bytes
        """
        raise NotImplementedError("{}.write", self.__class__.__name__)


class RenderedFile(RenderedElement):
    def __init__(self, src: FSFile):
        self.src = src

    def write(self, dst: FSFile):
        if dst.stat is not None and (
                self.src.stat.st_mtime > dst.stat.st_mtime
                or self.src.stat.st_size != dst.stat.st_size):
            shutil.copy2(self.abspath, dst.path)

    def content(self):
        with open(self.abspath, "rb") as fd:
            return fd.read()


class RenderedString(RenderedElement):
    def __init__(self, s):
        self.buf = s.encode("utf-8")

    def write(self, dst: FSFile):
        with open(dst.path, "wb") as out:
            out.write(self.buf)

    def content(self):
        return self.buf

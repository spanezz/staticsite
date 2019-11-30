from __future__ import annotations
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


class RenderedFile(RenderedElement):
    def __init__(self, src: File):
        self.src = src

    def write(self, dst: File):
        if dst.stat is None or (
                self.src.stat.st_mtime > dst.stat.st_mtime
                or self.src.stat.st_size != dst.stat.st_size):
            shutil.copy2(self.src.abspath, dst.abspath)

    def content(self):
        with open(self.src.abspath, "rb") as fd:
            return fd.read()


class RenderedString(RenderedElement):
    def __init__(self, s):
        self.buf = s.encode("utf-8")

    def write(self, dst: File):
        with open(dst.abspath, "wb") as out:
            out.write(self.buf)

    def content(self):
        return self.buf

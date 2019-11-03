from __future__ import annotations
import sys
import logging
import shutil

log = logging.getLogger()


class Settings:
    def __init__(self):
        from . import global_settings
        self.add_module(global_settings)

    def as_dict(self):
        res = {}
        for setting in dir(self):
            if setting.isupper():
                res[setting] = getattr(self, setting)
        return res

    def add_module(self, mod):
        """
        Add uppercase settings from mod into this module
        """
        for setting in dir(mod):
            if setting.isupper():
                setattr(self, setting, getattr(mod, setting))

    def load(self, pathname):
        """
        Load settings from a python file, importing only uppercase symbols
        """
        orig_dwb = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            # http://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path

            # Seriously, this should not happen in the standard library. You do not
            # break stable APIs. You can extend them but not break them. And
            # especially, you do not break stable APIs and then complain that people
            # stick to 2.7 until its death, and probably after.
            if sys.version_info >= (3, 5):
                import importlib.util
                spec = importlib.util.spec_from_file_location("staticsite.settings", pathname)
                user_settings = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(user_settings)
            else:
                from importlib.machinery import SourceFileLoader
                user_settings = SourceFileLoader("staticsite.settings", pathname).load_module()
        finally:
            sys.dont_write_bytecode = orig_dwb

        self.add_module(user_settings)


class RenderedFile:
    def __init__(self, abspath):
        self.abspath = abspath

    def write(self, dst):
        shutil.copy2(self.abspath, dst)

    def content(self):
        with open(self.abspath, "rb") as fd:
            return fd.read()


class RenderedString:
    def __init__(self, s):
        self.buf = s.encode("utf-8")

    def write(self, dst):
        with open(dst, "wb") as out:
            out.write(self.buf)

    def content(self):
        return self.buf

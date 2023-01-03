from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Optional, cast

try:
    import coloredlogs

    HAS_COLOREDLOGS = True
except ModuleNotFoundError:
    HAS_COLOREDLOGS = False


def _get_first_docstring_line(obj: Any) -> Optional[str]:
    if obj.__doc__ is None:
        raise RuntimeError(f"{obj!r} lacks a docstring")
    try:
        return cast(str, obj.__doc__).split("\n")[1].strip()
    except (AttributeError, IndexError):
        return None


class Fail(BaseException):
    """
    Failure that causes the program to exit with an error message.

    No stack trace is printed.
    """
    pass


class Success(BaseException):
    """
    Exception raised when a command has been successfully handled, and no
    further processing should happen
    """
    pass


class Command:
    """
    Base class for actions run from command line
    """

    NAME: Optional[str] = None

    def __init__(self, args: argparse.Namespace):
        if self.NAME is None:
            self.NAME = self.__class__.__name__.lower()
        self.args = args
        self.setup_logging()

    def setup_logging(self) -> None:
        FORMAT = "%(asctime)-15s %(levelname)s %(name)s %(message)s"
        if self.args.debug:
            level = logging.DEBUG
        elif self.args.verbose:
            level = logging.INFO
        else:
            level = logging.WARN

        if HAS_COLOREDLOGS:
            coloredlogs.install(level=level, fmt=FORMAT)
        else:
            logging.basicConfig(level=level, stream=sys.stderr, format=FORMAT)

    @classmethod
    def add_subparser(cls, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        if cls.NAME is None:
            cls.NAME = cls.__name__.lower()
        parser: argparse.ArgumentParser = subparsers.add_parser(
            cls.NAME,
            help=_get_first_docstring_line(cls),
        )
        parser.set_defaults(command=cls)
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="verbose output",
        ),
        parser.add_argument(
            "--debug",
            action="store_true",
            help="debugging output",
        ),
        return parser

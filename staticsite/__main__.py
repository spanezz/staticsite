#!/usr/bin/python3
import argparse
import importlib
import logging
import sys

from staticsite import __version__

log = logging.getLogger("ssite")


def main():
    parser = argparse.ArgumentParser(prog="ssite", description="Static site generator.")
    parser.add_argument(
        "--version", "-V", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(help="sub-command help", dest="command")

    modules = (
        "check",
        "dump",
        "dump_meta",
        "build",
        "serve",
        "new",
        "edit",
        "site",
        "meta",
        "shell",
    )
    for name in modules:
        importlib.import_module("staticsite.cmd." + name)

    from staticsite.cmd.command import COMMANDS

    for c in COMMANDS:
        c.add_subparser(subparsers)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
    else:
        handler = args.command(args)
        return handler.run()


def run_main():
    from staticsite.cmd.command import Fail, Success

    try:
        sys.exit(main())
    except Fail as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except Success:
        pass


if __name__ == "__main__":
    run_main()

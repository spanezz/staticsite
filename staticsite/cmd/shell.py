from __future__ import annotations

import logging
import os
from typing import Any

from .command import Fail, SiteCommand, register

log = logging.getLogger("shell")


@register
class Shell(SiteCommand):
    "start a shell with the global `site` set to the current site"

    # Taken from django's core/management/commands/shell.py

    shells = ['ipython', 'bpython', 'python']

    def ipython(self, **kw: Any) -> None:
        from IPython import start_ipython
        start_ipython(argv=[], user_ns=kw)

    def bpython(self, **kw: Any) -> None:
        import bpython
        bpython.embed(locals_=kw)

    def python(self, **kw: Any) -> None:
        import code

        # Set up a dictionary to serve as the environment for the shell, so
        # that tab completion works on objects that are imported at runtime.
        imported_objects = kw
        try:  # Try activating rlcompleter, because it's handy.
            import readline
        except ImportError:
            pass
        else:
            # We don't have to wrap the following import in a 'try', because
            # we already know 'readline' was imported successfully.
            import rlcompleter
            readline.set_completer(rlcompleter.Completer(imported_objects).complete)
            # Enable tab completion on systems using libedit (e.g. macOS).
            # These lines are copied from Lib/site.py on Python 3.4.
            readline_doc = getattr(readline, '__doc__', '')
            if readline_doc is not None and 'libedit' in readline_doc:
                readline.parse_and_bind("bind ^I rl_complete")
            else:
                readline.parse_and_bind("tab:complete")

        # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow system
        # conventions and get $PYTHONSTARTUP first then .pythonrc.py.
        for pythonrc in {os.environ.get("PYTHONSTARTUP"), os.path.expanduser('~/.pythonrc.py')}:
            if not pythonrc:
                continue
            if not os.path.isfile(pythonrc):
                continue
            try:
                with open(pythonrc) as handle:
                    exec(compile(handle.read(), pythonrc, 'exec'), imported_objects)
            except NameError:
                pass
        code.interact(local=imported_objects)

    def run(self) -> None:
        site = self.load_site()

        for shell in self.shells:
            try:
                getattr(self, shell)(site=site)
            except ModuleNotFoundError:
                pass

        raise Fail(f"Could not import {shell} interface.")

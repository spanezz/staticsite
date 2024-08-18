from __future__ import annotations

import io
from collections.abc import Callable
from typing import IO, Any, cast

#
# This is an unnecessarily complex wrapper to cope efficiently with YAML
# parsing in python.
#
# The current situation looks like:
#
#  * pyyaml is reasonably fast
#  * ruamel.yaml is unreasonably slow
#
# However, pyyaml doesn't support sort_keys until version 5.1, while
# ruamel.yaml can do unsorted dumping with no specific version requriements.
#
# So we mix and match, trying to use PyYAML for loading, and ruamel for
# dumping.
#

Load = Callable[[IO[str]], Any]
Loads = Callable[[str], Any]
Dump = Callable[[Any, IO[str]], None]
Dumps = Callable[[Any], str]

load_ruamel: Load | None
loads_ruamel: Loads | None
dump_ruamel: Dump | None
dumps_ruamel: Dumps | None

load_pyyaml: Load | None
loads_pyyaml: Loads | None
dump_pyyaml: Dump | None
dumps_pyyaml: Dumps | None

load: Load
loads: Loads
dump: Dump
dumps: Dumps

try:
    import ruamel.yaml

    yaml_loader = ruamel.yaml.YAML(typ="safe", pure=True)

    def loads_ruamel(string: str) -> Any:
        return yaml_loader.load(string)

    def load_ruamel(file: IO[str]) -> Any:
        return yaml_loader.load(file)

    # Hack to do unsorted serialization with ruamel
    yaml_dumper = ruamel.yaml.YAML(typ="rt", pure=True)
    yaml_dumper.allow_unicode = True
    yaml_dumper.default_flow_style = False
    # TODO: yaml does not have explicit_start typed correctly
    yaml_dumper.explicit_start = True  # type: ignore

    def dumps_ruamel(data: Any) -> str:
        # YAML dump with unsorted keys
        with io.StringIO() as fd:
            yaml_dumper.dump(data, fd)
            return fd.getvalue()

    def dump_ruamel(data: Any, file: IO[str]) -> None:
        yaml_dumper.dump(data, file)

except ModuleNotFoundError:
    load_ruamel = None
    loads_ruamel = None
    dump_ruamel = None
    dumps_ruamel = None

try:
    import yaml

    def loads_pyyaml(string: str) -> Any:
        return yaml.load(string, Loader=yaml.CLoader)

    def load_pyyaml(file: IO[str]) -> Any:
        return yaml.load(file, Loader=yaml.CLoader)

    def dumps_pyyaml(data: Any) -> str:
        # From pyyaml 5.1, one can add sort_keys=False
        # Before that version, it seems impossible to do unsorted serialization
        # with pyyaml
        # https://stackoverflow.com/questions/16782112/can-pyyaml-dump-dict-items-in-non-alphabetical-order
        return cast(
            str,
            yaml.dump(
                data,
                stream=None,
                default_flow_style=False,
                allow_unicode=True,
                explicit_start=True,
                Dumper=yaml.CDumper,
            ),
        )

    def dump_pyyaml(data: Any, file: IO[str]) -> None:
        yaml.dump(
            data,
            file,
            default_flow_style=False,
            allow_unicode=True,
            explicit_start=True,
            Dumper=yaml.CDumper,
        )

except ModuleNotFoundError:
    load_pyyaml = None
    loads_pyyaml = None
    dump_pyyaml = None
    dumps_pyyaml = None


# Prefer pyyaml for loading, because it's significantly faster
if load_pyyaml:
    load = load_pyyaml
elif load_ruamel:
    load = load_ruamel
else:
    raise RuntimeError("Neither PyYAML nor ruamel.YAML are installed")

if loads_pyyaml:
    loads = loads_pyyaml
elif loads_ruamel:
    loads = loads_ruamel
else:
    raise RuntimeError("Neither PyYAML nor ruamel.YAML are installed")


# Prefer ruamel for dumping, because it supports unsorted keys, that are useful
# when rendering archetypes
if dump_ruamel:
    dump = dump_ruamel
elif dump_pyyaml:
    dump = dump_pyyaml
else:
    raise RuntimeError("Neither PyYAML nor ruamel.YAML are installed")

if dumps_ruamel:
    dumps = dumps_ruamel
elif dumps_pyyaml:
    dumps = dumps_pyyaml
else:
    raise RuntimeError("Neither PyYAML nor ruamel.YAML are installed")

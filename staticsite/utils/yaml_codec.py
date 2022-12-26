from __future__ import annotations
from typing import TextIO, Optional, Callable, Any
import io

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

Load = Callable[[TextIO], Any]
Loads = Callable[[str], Any]
Dump = Callable[[Any, TextIO], None]
Dumps = Callable[[Any], str]

load_ruamel: Optional[Load]
loads_ruamel: Optional[Loads]
dump_ruamel: Optional[Dump]
dumps_ruamel: Optional[Dumps]

load_pyyaml: Optional[Load]
loads_pyyaml: Optional[Loads]
dump_pyyaml: Optional[Dump]
dumps_pyyaml: Optional[Dumps]

load: Load
loads: Loads
dump: Dump
dumps: Dumps

try:
    import ruamel.yaml

    yaml_loader = ruamel.yaml.YAML(typ="safe", pure=True)

    def loads_ruamel(string):
        return yaml_loader.load(string)

    def load_ruamel(file):
        return yaml_loader.load(file)

    # Hack to do unsorted serialization with ruamel
    yaml_dumper = ruamel.yaml.YAML(typ="rt", pure=True)
    yaml_dumper.allow_unicode = True
    yaml_dumper.default_flow_style = False
    yaml_dumper.explicit_start = True

    def dumps_ruamel(data):
        # YAML dump with unsorted keys
        with io.StringIO() as fd:
            yaml_dumper.dump(data, fd)
            return fd.getvalue()

    def dump_ruamel(data, file):
        yaml_dumper.dump(data, file)
except ModuleNotFoundError:
    load_ruamel = None
    loads_ruamel = None
    dump_ruamel = None
    dumps_ruamel = None

try:
    import yaml

    def loads_pyyaml(string):
        return yaml.load(string, Loader=yaml.CLoader)

    def load_pyyaml(file):
        return yaml.load(file, Loader=yaml.CLoader)

    def dumps_pyyaml(data):
        # From pyyaml 5.1, one can add sort_keys=False
        # Before that version, it seems impossible to do unsorted serialization
        # with pyyaml
        # https://stackoverflow.com/questions/16782112/can-pyyaml-dump-dict-items-in-non-alphabetical-order
        return yaml.dump(
                data, stream=None, default_flow_style=False,
                allow_unicode=True, explicit_start=True, Dumper=yaml.CDumper)

    def dump_pyyaml(data, file):
        yaml.dump(data, file, default_flow_style=False, allow_unicode=True, explicit_start=True, Dumper=yaml.CDumper)
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

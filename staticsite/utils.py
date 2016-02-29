# coding: utf-8

def parse_front_matter(lines):
    if not lines: return {}

    if lines[0] == "{":
        # JSON
        import json
        return json.loads("\n".join(lines))

    if lines[0] == "+++":
        # TOML
        import toml
        return toml.loads("\n".join(lines[1:-1]))

    if lines[0] == "---":
        # YAML
        import yaml
        return yaml.load("\n".join(lines[1:-1]), Loader=yaml.CLoader)

    return {}

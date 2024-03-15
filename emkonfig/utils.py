from typing import Any

import yaml


def load_yaml(path: str) -> dict[str, Any]:
    with open(path, "r") as f:
        content = yaml.safe_load(f)
    return content

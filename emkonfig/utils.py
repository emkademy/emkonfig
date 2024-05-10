import importlib
import time

from pathlib import Path
from typing import Any

import yaml

from emkonfig.external.hydra.instantiate import instantiate as hydra_instantiate

instantiate = hydra_instantiate


def load_yaml(path: str) -> dict[str, Any]:
    with open(path, "r") as f:
        content = yaml.safe_load(f)
    return content


def import_modules(dir_name: str, verbose: bool = False) -> None:
    start = time.time()
    for path in Path(dir_name).rglob("*.py"):
        if path.name.startswith("__"):
            continue
        module_path = path.with_suffix("").as_posix().replace("/", ".")

        try:
            importlib.import_module(module_path)
        except Exception as e:
            if verbose:
                print(f"Failed to import module: {module_path}")
                print(f"Error: {e}")
            continue

    end = time.time()
    print(f"Importing modules took {end - start:.2f} seconds")

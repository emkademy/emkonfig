import importlib
import time

from pathlib import Path
from typing import Any, Optional

import yaml

from emkonfig.external.hydra.instantiate import instantiate as hydra_instantiate

instantiate = hydra_instantiate


def load_yaml(path: str) -> dict[str, Any]:
    with open(path, "r") as f:
        content = yaml.safe_load(f)
    return content


def import_modules(dir_name: str, exclude: list[str] | set[str] | None = None, verbose: bool = False) -> None:
    if exclude is None:
        exclude = set()
    exclude = set(exclude)

    start = time.time()
    for path in Path(dir_name).rglob("*.py"):
        if path.name.startswith("__"):
            continue
        module_path = path.with_suffix("").as_posix().replace("/", ".")
        if module_path in exclude:
            if verbose:
                print(f"Skipping module: {module_path}")
            continue

        if verbose:
            print(f"Importing module: {module_path}")

        try:
            importlib.import_module(module_path)
        except Exception as e:
            if verbose:
                print(f"Failed to import module: {module_path}")
                print(f"Error: {e}")
            continue

    end = time.time()
    print(f"Importing modules took {end - start:.2f} seconds")

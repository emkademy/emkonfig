import importlib
import time

from typing import Any

import yaml

from upath import UPath

from emkonfig.external.hydra.instantiate import instantiate as hydra_instantiate

instantiate = hydra_instantiate


def merge_dicts(dict1: dict, dict2: dict, concat_lists=True) -> dict:
    for key in dict2:
        if key in dict1:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                merge_dicts(dict1[key], dict2[key])
            elif isinstance(dict1[key], list) and isinstance(dict2[key], list):
                if concat_lists:
                    dict1[key] = dict1[key] + dict2[key]
                else:
                    dict1[key] = dict2[key]
            else:
                dict1[key] = dict2[key]
        else:
            dict1[key] = dict2[key]
    return dict1


def load_yaml(path: str) -> dict[str, Any]:
    with UPath(path).open("r") as f:
        content = yaml.safe_load(f)
    return content


def import_modules(dir_name: str, exclude: list[str] | set[str] | None = None, verbose: bool = False) -> None:
    if exclude is None:
        exclude = set()
    exclude = set(exclude)

    start = time.time()
    for path in UPath(dir_name).rglob("*.py"):
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

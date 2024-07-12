import importlib
import json
import logging
import os
import time

from pathlib import Path
from typing import Any, Dict, Union

import yaml

from fsspec import AbstractFileSystem, filesystem
from omegaconf import DictConfig, OmegaConf

from emkonfig.external.hydra.instantiate import instantiate as hydra_instantiate

logger = logging.getLogger()

GS_PREFIX = "gs://"
GOOGLE_CLOUD_SERVICE_FILE_SYSTEM = "gcs"
LOCAL_FILE_SYSTEM = "file"
LOCAL_GCS_CACHE_PATH = "/tmp/gcp_cache"


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


def choose_file_system(path: str) -> AbstractFileSystem:
    return filesystem(GOOGLE_CLOUD_SERVICE_FILE_SYSTEM) if path.startswith(GS_PREFIX) else filesystem(LOCAL_FILE_SYSTEM)


def open_file(path: str, mode: str = "r") -> Any:
    file_system = choose_file_system(path)
    return file_system.open(path, mode)


def rename_file(path1: str, path2: str) -> Any:
    file_system = choose_file_system(path1)
    return file_system.rename(path1, path2)


def isdir(path: str) -> bool:
    file_system = choose_file_system(path)
    is_dir: bool = file_system.isdir(path)
    return is_dir


def isfile(path: str) -> bool:
    file_system = choose_file_system(path)
    is_file: bool = file_system.isfile(path)
    return is_file


def makedirs(path: str) -> None:
    file_system = choose_file_system(path)
    file_system.makedirs(path, exist_ok=True)


def list_paths(data_path: str, check_path_suffix: bool = False, path_suffix: str = ".csv") -> list[str]:
    file_system = choose_file_system(data_path)
    if not file_system.isdir(data_path):
        return []
    paths: list[str] = file_system.ls(data_path)
    if check_path_suffix:
        paths = [path for path in paths if path.endswith(path_suffix)]
    if GOOGLE_CLOUD_SERVICE_FILE_SYSTEM in file_system.protocol:
        gs_paths: list[str] = [GS_PREFIX + file_path for file_path in paths]
        return gs_paths
    else:
        return paths


def remove_path(path: str) -> None:
    file_system = choose_file_system(path)
    file_system.rm(path, recursive=True)


def copy_dir(source_dir: str, target_dir: str) -> None:
    logger.info(f"Copying dir {source_dir} to {target_dir}")
    if not isdir(target_dir):
        makedirs(target_dir)
    source_files = list_paths(source_dir)
    for source_file in source_files:
        target_file = os.path.join(target_dir, os.path.basename(source_file))
        if isfile(source_file):
            with open_file(source_file, mode="rb") as source, open_file(target_file, mode="wb") as target:
                content = source.read()
                target.write(content)
        else:
            raise ValueError(f"Copying supports flat dirs only – failed on {source_file}")


def copy_file(source_file: str, target_path: str) -> None:
    logger.info(f"Copying file from {source_file} to {target_path}")
    with open_file(source_file, mode="rb") as source, open_file(target_path, mode="wb") as target:
        content = source.read()
        target.write(content)


def convert_gcs_path_to_local_path(path: str) -> str:
    if path.startswith(GS_PREFIX):
        path = path.rstrip("/")
        local_path = os.path.join(LOCAL_GCS_CACHE_PATH, os.path.split(path)[-1])
        return local_path
    return path


def cache_gcs_resource_locally(path: str) -> str:
    if path.startswith(GS_PREFIX):
        local_path = convert_gcs_path_to_local_path(path)

        if os.path.exists(local_path):
            return local_path

        if isdir(path):
            os.makedirs(local_path, exist_ok=True)
            copy_dir(path, local_path)
        else:
            os.makedirs(LOCAL_GCS_CACHE_PATH, exist_ok=True)
            copy_file(path, local_path)
        return local_path

    return path


def wait_for_file(file_path: str, timeout_seconds: int = 10 * 60) -> None:
    counter = 0
    sleep_seconds = 10
    while not isfile(file_path):
        time.sleep(sleep_seconds)

        counter += sleep_seconds

        if counter >= timeout_seconds:
            raise RuntimeError(f"Waited {timeout_seconds}s for file: {file_path}, but it didn't appear")


def load_json(path: str) -> Union[dict, list]:
    with open(path, "r") as f:
        return json.load(f)  # type: ignore

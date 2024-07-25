import argparse
import re

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Iterator

from omegaconf import OmegaConf
from upath import UPath

from emkonfig.registry import _EMKONFIG_DEFAULTS_REGISTRY, _EMKONFIG_REGISTRY
from emkonfig.utils import merge_dicts


class Syntax(Enum):
    CLASS_SLUG = "class_slug"
    REFERENCE_KEY = "reference_key"
    REFERENCE_YAML = "reference_yaml"


class Parser(ABC):
    @abstractmethod
    def parse(self, content: dict[str, Any] | list[Any], full_content: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        ...


class ReferenceYamlParser(Parser):
    def parse(
        self, content: dict[str, Any] | list[Any], full_content: dict[str, Any] | None = None, from_defaults_list: bool = False
    ) -> dict[str, Any] | list[Any]:
        try:
            new_content = content.copy()
        except AttributeError:
            return content

        assert isinstance(content, dict), f"Invalid value for reference yaml parser: {content}"
        assert isinstance(new_content, dict), f"Invalid value for reference yaml parser: {new_content}"

        for key, value in content.items():
            if isinstance(value, dict):
                new_content[key] = self.parse(value, full_content)
            elif self.is_yaml_reference(value) or from_defaults_list:
                reference_yaml = value[2:-1] if not from_defaults_list else value
                if key == "_":
                    new_content.update(FullConfigParser(reference_yaml).parse())
                    del new_content[key]
                else:
                    new_content[key] = FullConfigParser(reference_yaml).parse()
        return new_content

    @staticmethod
    def is_yaml_reference(value: Any) -> bool:
        return isinstance(value, str) and value.startswith("${") and value.endswith(".yaml}")


class ReferenceKeyParser(Parser):
    def parse(self, content: dict[str, Any] | list[Any], full_content: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        assert full_content is not None
        try:
            new_content = content.copy()
        except AttributeError:
            return content

        assert isinstance(content, dict), f"Invalid value for reference key parser: {content}"
        assert isinstance(new_content, dict), f"Invalid value for reference key parser: {new_content}"

        for key, value in content.items():
            if isinstance(value, dict):
                new_content[key] = self.parse(value, full_content)
            elif isinstance(value, list):
                new_values = []
                for item in value:
                    if self.is_reference_key(item):
                        assert isinstance(item, str), f"Invalid value for reference key parser: {item}"
                        new_values.append(self.get_value_from_dot_notation(item, full_content))
                    else:
                        new_values.append(self.parse(item, full_content))
                new_content[key] = new_values

            if self.is_reference_key(value):
                assert isinstance(value, str), f"Invalid value for reference key parser: {value}"
                new_value = self.get_value_from_dot_notation(value, full_content)
                new_content[key] = self.parse(new_value, full_content)

        return new_content

    @staticmethod
    def is_reference_key(value: Any) -> bool:
        return isinstance(value, str) and value.startswith("${") and value.endswith("}") and not value.endswith(".yaml}")

    def get_value_from_dot_notation(self, reference_key: str, content: dict[str, Any]) -> Any:
        reference_key = reference_key[2:-1]
        keys = reference_key.split(".")
        value = content
        for key in keys:
            try:
                matches = re.findall(r"^.*?\[[^\d]*(\d+)[^\d]*\].*$", key)
                if len(matches) > 0:
                    match = matches[0]
                    key = key.replace(f"[{match}]", "")
                    value = value[key][int(match)]
                else:
                    value = value[key]
            except KeyError as err:
                print(err)
                raise KeyError(f"Invalid reference key: {reference_key}")
        return value


class ClassSlugParser(Parser):
    def parse(
        self, content: dict[str, Any] | list[Any], full_content: dict[str, Any] | None = None, seen: set[str] = set()
    ) -> dict[str, Any] | list[Any]:
        try:
            new_content = content.copy()
        except AttributeError:
            return content

        assert isinstance(content, dict), f"Invalid value for class slug parser: {content}"
        assert isinstance(new_content, dict), f"Invalid value for class slug parser: {new_content}"

        for key, value in content.items():
            if isinstance(value, list):
                new_values = []
                for item in value:
                    new_values.append(self.parse(item, full_content, seen))
                new_content[key] = new_values
            elif isinstance(value, dict):
                if key not in seen:
                    new_content[key] = self.parse(value, full_content, seen)

            if self.is_class_slug_key(key):
                value = new_content.get(key, value)
                if value is None:
                    value = {}
                assert isinstance(value, dict), f"Invalid value for class slug key parser: {value}"
                class_slug, new_key = self.parse_class_slug_key(key)
                cls = _EMKONFIG_REGISTRY[class_slug]
                cls_location = cls.__module__ + "." + cls.__name__
                parameters = _EMKONFIG_DEFAULTS_REGISTRY[class_slug]
                parameters.update(value)
                if new_key == "_":
                    new_content.update({"_target_": cls_location, **parameters})
                else:
                    new_content[new_key] = {"_target_": cls_location, **parameters}
                seen.add(new_key)
                del new_content[key]

        return new_content

    @staticmethod
    def parse_class_slug_key(key: str) -> tuple[str, str]:
        if " as " in key:
            class_slug, new_key = key[2:-1].split(" as ")
        else:
            class_slug = key[2:-1]
            new_key = key[2:-1]
        return class_slug, new_key

    @staticmethod
    def is_class_slug_key(key: str) -> bool:
        return isinstance(key, str) and key.startswith("_{") and key.endswith("}")


class ArgsParser(Parser):
    def __init__(self) -> None:
        self.sequence_parser = SequenceParser()

    def parse(self, content: dict[str, Any] | list[Any], full_content: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        assert isinstance(content, dict), f"Invalid value for args parser: {content}"
        overwrites = self.parse_overwrites()
        merged_content = merge_dicts(content, overwrites, concat_lists=False)
        merged_content = self.sequence_parser.parse(merged_content)
        return merged_content

    def parse_overwrites(self) -> dict[str, Any]:
        parser = argparse.ArgumentParser()
        parser.add_argument("--overwrites", type=str, nargs="*", default=[])

        args, _ = parser.parse_known_args()
        overwrites_dict = OmegaConf.from_dotlist(args.overwrites)
        return OmegaConf.to_container(overwrites_dict)  # type: ignore


class DefaultsListParser(Parser):
    def __init__(self, configs_dir: str | UPath) -> None:
        self.configs_dir = UPath(configs_dir)
        self.referance_yaml_parser = ReferenceYamlParser()

    def parse(self, content: dict[str, Any] | list[Any], full_content: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        assert isinstance(content, dict), f"Invalid value for defaults list parser: {content}"

        defaults_list = content["defaults"]
        parsed_content: dict[str, Any] = {}
        for defaults in defaults_list:
            dir_and_new_key, value = defaults.popitem()
            dir_and_new_key = dir_and_new_key.split("@")
            if len(dir_and_new_key) == 1:
                dir = dir_and_new_key[0]
                new_key = dir.replace("/", ".")
            else:
                dir = dir_and_new_key[0]
                new_key = dir_and_new_key[1]

            parsed_defaults_list_content = self._get_parsed_yaml_content(dir, value, new_key)
            parsed_content = merge_dicts(parsed_content, parsed_defaults_list_content, concat_lists=False)
        return parsed_content

    def _get_parsed_yaml_content(self, dir: str, value: str | list[str], new_key: str) -> dict[str, Any]:
        parsed_values = []
        for item in value if isinstance(value, list) else [value]:
            yaml_location = self.configs_dir / dir / f"{item}.yaml"
            to_parse_content = OmegaConf.to_container(OmegaConf.from_dotlist([f"{new_key}={yaml_location}"]))
            parsed_defaults_list_content = self.referance_yaml_parser.parse(to_parse_content, from_defaults_list=True)  # type: ignore
            assert isinstance(parsed_defaults_list_content, dict), f"Invalid value for defaults list parser: {parsed_defaults_list_content}"
            parsed_value = parsed_defaults_list_content.popitem()[1]
            parsed_values.append(parsed_value)
        return OmegaConf.to_container(OmegaConf.from_dotlist([f"{new_key}={parsed_values[0] if len(parsed_values) == 1 else parsed_values}"]))  # type: ignore


class SequenceParser:
    def __init__(self, parse_order: list[Syntax] | None = None, syntax_to_parser: dict[Syntax, Parser] | None = None) -> None:
        if parse_order is None:
            parse_order = [Syntax.REFERENCE_YAML, Syntax.CLASS_SLUG, Syntax.REFERENCE_KEY]
        self.parse_order = parse_order

        if syntax_to_parser is None:
            syntax_to_parser = {
                Syntax.CLASS_SLUG: ClassSlugParser(),
                Syntax.REFERENCE_KEY: ReferenceKeyParser(),
                Syntax.REFERENCE_YAML: ReferenceYamlParser(),
            }

        self.syntax_to_parser = syntax_to_parser

        if not all(syntax in self.syntax_to_parser for syntax in self.parse_order):
            print(f"{self.parse_order=}")
            print(f"{self.syntax_to_parser=}")
            raise ValueError("parse_order contains syntax not in syntax_to_parser")

    def parse(self, content: dict[str, Any]) -> dict[str, Any]:
        new_content = content.copy()
        for syntax in self.parse_order:
            assert isinstance(new_content, dict), f"Invalid value for sequence parser: {new_content}"
            new_content = self.syntax_to_parser[syntax].parse(new_content, new_content)  # type: ignore

        assert isinstance(new_content, dict), f"Invalid value for sequence parser: {new_content}"
        return new_content


class FullConfigParser:
    def __init__(self, path: str) -> None:
        self.configs_dir = UPath(path).absolute().parent  # type: ignore
        self.path = path
        self.defaults_list_parser = DefaultsListParser(self.configs_dir)
        self.parser = SequenceParser(parse_order=[Syntax.REFERENCE_YAML, Syntax.CLASS_SLUG])
        self.referance_key_parser = ReferenceKeyParser()

    def parse(self) -> dict[str, Any]:
        parsed_content = self.line_by_line_parser()
        parsed_content = self.referance_key_parser.parse(parsed_content, parsed_content)  # type: ignore
        assert isinstance(parsed_content, dict), f"Invalid value for full config parser: {parsed_content}"
        return parsed_content

    def line_by_line_parser(self) -> dict[str, Any]:
        parsed_content: dict[str, Any] = {}
        for key in self.yaml_iterator():
            key_yaml = OmegaConf.to_container(OmegaConf.create(key))
            if "defaults" in key_yaml:  # type: ignore
                parsed_key_yaml = self.defaults_list_parser.parse(key_yaml)  # type: ignore
            else:
                parsed_key_yaml = self.parser.parse(key_yaml)  # type: ignore

            assert isinstance(parsed_key_yaml, dict), f"Invalid value for full config parser: {parsed_key_yaml}"
            parsed_content = merge_dicts(
                parsed_content,
                parsed_key_yaml,
                concat_lists=False,
            )
        return parsed_content

    def yaml_iterator(self) -> Iterator[str]:
        with open(self.path, "r") as f:
            key = ""
            started = False
            for line in f:
                if len(line.strip()) == 0:
                    continue
                if line[0] != " " and started:
                    if len(key) == 0:
                        key = line.strip()

                    yield key
                    key = ""
                    started = False
                key += line
                started = True

            yield key

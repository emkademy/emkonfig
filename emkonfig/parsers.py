import argparse
import re

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Iterator

from omegaconf import OmegaConf

from emkonfig.registry import _EMKONFIG_DEFAULTS_REGISTRY, _EMKONFIG_REGISTRY
from emkonfig.utils import merge_dicts


class Syntax(Enum):
    CLASS_SLUG = "class_slug"
    REFERENCE_KEY = "reference_key"
    REFERENCE_YAML = "reference_yaml"


class Parser(ABC):
    @abstractmethod
    def parse(self, full_content: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        ...


class ReferenceYamlParser(Parser):
    def parse(self, full_content: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        try:
            new_content = content.copy()
        except AttributeError:
            return content

        for key, value in content.items():
            if isinstance(value, dict):
                new_content[key] = self.parse(full_content, value)
            elif self.is_yaml_reference(value):
                reference_yaml = value[2:-1]
                if key == "_":
                    new_content.update(FullConfigParser(reference_yaml).parse())
                    del new_content[key]
                else:
                    new_content[key] = FullConfigParser(reference_yaml).parse()
        return new_content

    @staticmethod
    def is_yaml_reference(value: Any) -> bool:
        return isinstance(value, str) and value.startswith("${") and value.endswith(".yaml}")


class ClassSlugParser(Parser):
    def parse(self, full_content: dict[str, Any], content: dict[str, Any], seen=set()) -> dict[str, Any]:
        try:
            new_content = content.copy()
        except AttributeError:
            return content

        for key, value in content.items():
            if isinstance(value, list):
                new_values = []
                for item in value:
                    new_values.append(self.parse(full_content, item, seen))
                new_content[key] = new_values
            elif isinstance(value, dict):
                if key not in seen:
                    new_content[key] = self.parse(full_content, value, seen)

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


class ReferenceKeyParser(Parser):
    def parse(self, full_content: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        try:
            new_content = content.copy()
        except AttributeError:
            return content

        for key, value in content.items():
            if isinstance(value, dict):
                new_content[key] = self.parse(full_content, value)
            elif isinstance(value, list):
                new_values = []
                for item in value:
                    if self.is_reference_key(item):
                        assert isinstance(item, str), f"Invalid value for reference key parser: {item}"
                        new_values.append(self.get_value_from_dot_notation(full_content, item))
                    else:
                        new_values.append(self.parse(full_content, item))
                new_content[key] = new_values

            if self.is_reference_key(value):
                assert isinstance(value, str), f"Invalid value for reference key parser: {value}"
                new_value = self.get_value_from_dot_notation(full_content, value)
                new_content[key] = self.parse(full_content, new_value)

        return new_content

    @staticmethod
    def is_reference_key(value: Any) -> bool:
        return isinstance(value, str) and value.startswith("${") and value.endswith("}") and not value.endswith(".yaml}")

    def get_value_from_dot_notation(self, content: dict[str, Any], reference_key: str) -> Any:
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


class ArgsParser(Parser):
    def __init__(self) -> None:
        self.sequence_parser = SequenceParser()

    def parse(self, full_content: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        overwrites = self.parse_overwrites()
        merged_content = merge_dicts(full_content, overwrites, concat_lists=False)
        merged_content = self.sequence_parser.parse(merged_content)
        return merged_content

    def parse_overwrites(self) -> dict[str, Any]:
        parser = argparse.ArgumentParser()
        parser.add_argument("--overwrites", type=str, nargs="*", default=[])

        args = parser.parse_args()
        overwrites_dict = OmegaConf.from_dotlist(args.overwrites)
        return OmegaConf.to_container(overwrites_dict)  # type: ignore


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
            new_content = self.syntax_to_parser[syntax].parse(new_content, new_content)
        return new_content


class FullConfigParser:
    def __init__(self, path: str) -> None:
        self.path = path
        self.parser = SequenceParser(parse_order=[Syntax.REFERENCE_YAML, Syntax.CLASS_SLUG])
        self.referance_key_parser = ReferenceKeyParser()

    def parse(self) -> dict[str, Any]:
        parsed_content = self.line_by_line_parser()
        parsed_content = self.referance_key_parser.parse(parsed_content, parsed_content)
        return parsed_content

    def line_by_line_parser(self) -> dict[str, Any]:
        parsed_content = {}
        for key in self.yaml_iterator():
            key_yaml = OmegaConf.to_container(OmegaConf.create(key))  # type: ignore
            parsed_key_yaml = self.parser.parse(key_yaml)  # type: ignore
            parsed_content = merge_dicts(
                parsed_content,
                parsed_key_yaml,
                concat_lists=False,
            )
        return parsed_content

    def yaml_iterator(self) -> Iterator[str]:
        with open(self.path, "r") as f:
            key = ""
            for line in f:
                if len(line.strip()) == 0:
                    continue
                if line[0] != " ":
                    if len(key) == 0:
                        key = line.strip()

                    yield key
                    key = ""
                key += line

            yield key

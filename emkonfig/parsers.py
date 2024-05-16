import re

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from omegaconf import DictConfig, OmegaConf

from emkonfig.registry import _EMKONFIG_DEFAULTS_REGISTRY, _EMKONFIG_REGISTRY
from emkonfig.utils import load_yaml


class Syntax(Enum):
    STANDARD = "standard"
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
                    new_content.update(SequenceParser(reference_yaml).parse())
                    del new_content[key]
                else:
                    new_content[key] = SequenceParser(reference_yaml).parse()
        return new_content

    def is_yaml_reference(self, value: Any) -> bool:
        return isinstance(value, str) and value.startswith("${") and value.endswith(".yaml}")


class ClassSlugParser(Parser):
    def parse(self, full_content: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
        try:
            new_content = content.copy()
        except AttributeError:
            return content

        for key, value in content.items():
            if isinstance(value, list):
                new_values = []
                for item in value:
                    new_values.append(self.parse(full_content, item))
                new_content[key] = new_values
            elif isinstance(value, dict):
                new_content[key] = self.parse(full_content, value)

            if isinstance(key, str) and key.startswith("_{") and key.endswith("}"):
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

    def is_reference_key(self, value: Any) -> bool:
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


class SequenceParser:
    def __init__(self, path: str, parse_order: list[Syntax] | None = None, syntax_to_parser: dict[Syntax, Parser] | None = None) -> None:
        self.original_yaml_content = load_yaml(path)

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
            raise ValueError("parse_order contains syntax not in syntax_to_parser")

    def parse(self, content: dict[str, Any] | None = None) -> DictConfig:
        if content is None:
            content = self.original_yaml_content

        new_content = content.copy()
        for syntax in self.parse_order:
            new_content = self.syntax_to_parser[syntax].parse(new_content, new_content)
        return OmegaConf.create(new_content)

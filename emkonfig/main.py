import re

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from emkonfig.register import _EMKONFIG_REGISTRY, register
from emkonfig.utils import load_yaml


@register("some_class")
class SomeClass:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def __repr__(self) -> str:
        return f"SomeClass({self.kwargs=})"


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
            elif isinstance(value, str) and value.startswith("${") and value.endswith(".yaml}"):
                reference_yaml = value[2:-1]
                new_content[key] = load_yaml(reference_yaml)
        return new_content


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
                assert isinstance(value, dict), f"Invalid value for class slug key parser: {value}"
                class_slug, new_key = self.parse_class_slug_key(key)
                cls = _EMKONFIG_REGISTRY[class_slug]
                cls_location = cls.__module__ + "." + cls.__name__
                new_content[new_key] = {"_target_": cls_location, **value}
                del new_content[key]

        return new_content

    @staticmethod
    def parse_class_slug_key(key: str) -> tuple[str, str]:
        if "as" in key:
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
        return isinstance(value, str) and value.startswith("${") and value.endswith("}")

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


class Emkonfig:
    def __init__(self, path: str) -> None:
        self.original_yaml_context = load_yaml(path)
        self.parse_order = [Syntax.REFERENCE_YAML, Syntax.CLASS_SLUG, Syntax.REFERENCE_KEY]
        self.syntax_to_parser = {
            Syntax.CLASS_SLUG: ClassSlugParser(),
            Syntax.REFERENCE_KEY: ReferenceKeyParser(),
            Syntax.REFERENCE_YAML: ReferenceYamlParser(),
        }

    def parse(self, content: dict[str, Any]) -> dict[str, Any]:
        new_content = content.copy()
        for syntax in self.parse_order:
            new_content = self.syntax_to_parser[syntax].parse(new_content, new_content)
        return new_content

    # def parse_key_value(self, key: str | None, value: Any) -> tuple[str | None, Any]:
    #     new_key = key
    #
    #     if isinstance(value, list):
    #         new_value = []
    #         for item in value:
    #             _, new_item = self.parse_key_value(None, item)
    #             new_value.append(new_item)
    #     elif isinstance(value, dict):
    #         new_value = self.parse_yaml(value)
    #     else:
    #         value_syntax = get_syntax_type(value)
    #         new_key, new_value = self.syntax_to_parser[value_syntax].parse(self.original_yaml_context, key, value)
    #
    #     return new_key, new_value
    #
    # def parse_yaml(self, content: dict[str, Any]) -> dict[str, Any]:
    #     new_content = {}
    #
    #     for key, value in content.items():
    #         new_key, new_value = self.parse_key_value(key, value)
    #         try:
    #             new_content[new_key] = new_value
    #         except Exception as err:
    #             print(err)
    #             print(f"{new_key=}, {new_value=}")
    #             exit(0)
    #
    #     return content


def main() -> None:
    from omegaconf import OmegaConf

    config = Emkonfig("configs/config.yaml")
    print(OmegaConf.to_yaml(config.parse(config.original_yaml_context)))


if __name__ == "__main__":
    main()

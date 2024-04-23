from enum import Enum
from typing import Any

from omegaconf import DictConfig, OmegaConf

from emkonfig.parsers import ClassSlugParser, Parser, ReferenceKeyParser, ReferenceYamlParser
from emkonfig.utils import load_yaml


class Syntax(Enum):
    STANDARD = "standard"
    CLASS_SLUG = "class_slug"
    REFERENCE_KEY = "reference_key"
    REFERENCE_YAML = "reference_yaml"


class Emkonfig:
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

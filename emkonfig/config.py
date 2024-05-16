from typing import Any

from omegaconf import DictConfig, OmegaConf

from emkonfig.parsers import Parser, SequenceParser, Syntax


class Emkonfig:
    def __init__(self, path: str, parse_order: list[Syntax] | None = None, syntax_to_parser: dict[Syntax, Parser] | None = None) -> None:
        self.parser = SequenceParser(path, parse_order, syntax_to_parser)

    @property
    def original_yaml_content(self) -> dict[str, Any]:
        return self.parser.original_yaml_content

    def parse(self, content: dict[str, Any] | None = None) -> DictConfig:
        return self.parser.parse(content)

    def print(self, config: DictConfig) -> None:
        print(OmegaConf.to_yaml(config))

    def __repr__(self) -> str:
        return OmegaConf.to_yaml(self.parse())

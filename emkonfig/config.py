from omegaconf import DictConfig, OmegaConf

from emkonfig.parsers import FullConfigParser


class Emkonfig:
    def __init__(self, path: str) -> None:
        self.parser = FullConfigParser(path)
        self.config: DictConfig | None = None

    def parse(self) -> DictConfig:
        if self.config is None:
            parsed_config = self.parser.parse()
            self.config = OmegaConf.create(parsed_config)
        return self.config

    def print(self, config: DictConfig) -> None:
        print(OmegaConf.to_yaml(config))

    def __repr__(self) -> str:
        return OmegaConf.to_yaml(self.config)

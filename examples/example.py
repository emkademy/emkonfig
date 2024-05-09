from omegaconf import OmegaConf

import examples.classes

from emkonfig.config import Emkonfig

if __name__ == "__main__":
    emkonfig = Emkonfig("examples/configs/config.yaml")
    config = emkonfig.parse()
    print(OmegaConf.to_yaml(config))

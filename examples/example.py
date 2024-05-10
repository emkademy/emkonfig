from emkonfig.config import Emkonfig
from emkonfig.utils import import_modules, instantiate

import_modules("examples")


if __name__ == "__main__":
    emkonfig = Emkonfig("examples/configs/config.yaml")
    config = emkonfig.parse()
    emkonfig.print(config)
    some_class = instantiate(config.nihao)
    print(some_class)

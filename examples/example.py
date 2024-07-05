from emkonfig.config import Emkonfig
from emkonfig.registry import register, register_class
from emkonfig.utils import import_modules, instantiate

import_modules("examples")


class Lala:
    def __init__(self, asd="3") -> None:
        self.asd = asd


register_class("lala", Lala, partial=True)


if __name__ == "__main__":
    emkonfig = Emkonfig("examples/configs/config.yaml")
    config = emkonfig.parse()
    emkonfig.print(config)
    some_class = instantiate(config.nihao)
    print(some_class)

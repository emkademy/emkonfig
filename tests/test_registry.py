from emkonfig.registry import _EMKONFIG_DEFAULTS_REGISTRY, _EMKONFIG_REGISTRY, get_default_arguments, register, register_class


@register("test_class")
class _TestClass:
    def __init__(
        self,
        arg0: str,
        arg1: str = "arg1",
        arg2: int = 3,
        arg3: float = 3.14,
        arg4: list[float] = [1.2, 3.4, 5.6],
        arg5: dict[str, int] = {"key1": 1, "key2": 2},
    ) -> None:
        self.arg0 = arg0
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5


def test_get_default_arguments():
    defaults = get_default_arguments(_TestClass)
    assert defaults == {"arg1": "arg1", "arg2": 3, "arg3": 3.14, "arg4": [1.2, 3.4, 5.6], "arg5": {"key1": 1, "key2": 2}}


def test_register():
    test_cls = _TestClass("")
    assert isinstance(test_cls, _TestClass)

    assert _EMKONFIG_REGISTRY == {"test_class": _TestClass}
    assert _EMKONFIG_DEFAULTS_REGISTRY == {
        "test_class": {
            "arg1": "arg1",
            "arg2": 3,
            "arg3": 3.14,
            "arg4": [1.2, 3.4, 5.6],
            "arg5": {"key1": 1, "key2": 2},
        }
    }


def test_register_class():
    class _TestClass2:
        def __init__(self, arg0: str, arg1: str = "arg1") -> None:
            self.arg0 = arg0
            self.arg1 = arg1

    register_class("test_class2", _TestClass2)
    assert _EMKONFIG_REGISTRY == {
        "test_class": _TestClass,
        "test_class2": _TestClass2,
    }
    assert _EMKONFIG_DEFAULTS_REGISTRY == {
        "test_class": {
            "arg1": "arg1",
            "arg2": 3,
            "arg3": 3.14,
            "arg4": [1.2, 3.4, 5.6],
            "arg5": {"key1": 1, "key2": 2},
        },
        "test_class2": {"arg1": "arg1"},
    }

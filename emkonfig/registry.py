import inspect

from typing import Any

_EMKONFIG_REGISTRY = {}
_EMKONFIG_DEFAULTS_REGISTRY = {}


def get_default_arguments(cls: Any) -> dict[str, Any]:
    signature = inspect.signature(cls)
    defaults = {}
    for parameter_name, parameter in signature.parameters.items():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD or parameter.default is inspect._empty:
            continue

        defaults[parameter_name] = parameter.default

    return defaults


def register(cls_slug: str):
    def decorator(cls):
        if cls_slug not in _EMKONFIG_DEFAULTS_REGISTRY:
            _EMKONFIG_DEFAULTS_REGISTRY[cls_slug] = get_default_arguments(cls)
            _EMKONFIG_REGISTRY[cls_slug] = cls
        return cls

    return decorator


def register_class(slug: str, cls, partial: bool = False, **kwargs) -> None:
    if slug not in _EMKONFIG_DEFAULTS_REGISTRY:
        default_arguments = get_default_arguments(cls)
        default_arguments.update(kwargs)
        if partial:
            default_arguments["_partial_"] = True
        _EMKONFIG_DEFAULTS_REGISTRY[slug] = default_arguments
        _EMKONFIG_REGISTRY[slug] = cls

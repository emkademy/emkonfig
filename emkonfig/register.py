_EMKONFIG_REGISTRY = {}


def register(cls_slug: str):
    def decorator(cls):
        _EMKONFIG_REGISTRY[cls_slug] = cls
        return cls

    return decorator

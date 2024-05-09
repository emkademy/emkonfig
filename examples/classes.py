from emkonfig.registry import register


@register("some_class")
class SomeClass:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __repr__(self):
        return f"SomeClass({self.kwargs})"


@register("some_other_class")
class SomeOtherClass:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __repr__(self):
        return f"SomeOtherClass({self.kwargs})"


@register("yet_another_class")
class YetAnotherClass:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __repr__(self):
        return f"YetAnotherClass({self.kwargs})"

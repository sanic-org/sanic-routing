import re
import typing as t
from types import SimpleNamespace


class ParamInfo:
    __slots__ = (
        "cast",
        "ctx",
        "label",
        "name",
        "pattern",
        "priority",
        "raw_path",
        "regex",
    )

    def __init__(
        self,
        name: str,
        raw_path: str,
        label: str,
        cast: t.Callable[[str], t.Any],
        pattern: re.Pattern,
        regex: bool,
        priority: int,
    ) -> None:
        self.name = name
        self.raw_path = raw_path
        self.label = label
        self.cast = cast
        self.pattern = pattern
        self.regex = regex
        self.priority = priority
        self.ctx = SimpleNamespace()

    def process(
        self,
        params: t.Dict[str, t.Any],
        value: t.Union[str, t.Tuple[str, ...]],
    ) -> None:
        ...

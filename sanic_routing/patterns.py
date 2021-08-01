import re
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Pattern, Tuple, Type

from sanic_routing.exceptions import InvalidUsage, NotFound

from .parameter import ParamInfo


def parse_date(d):
    return datetime.strptime(d, "%Y-%m-%d").date()


def alpha(param: str) -> str:
    if not param.isalpha():
        raise ValueError(f"Value {param} contains non-alphabetic chracters")
    return param


def slug(param: str) -> str:
    if not REGEX_TYPES["slug"][1].match(param):
        raise ValueError(f"Value {param} does not match the slug format")
    return param


def ext(param: str) -> Tuple[str, str]:
    if not param.count(".") >= 1:
        raise ValueError(f"Value {param} does not match the ext format")
    name, ext = param.rsplit(".", 1)
    if not ext.isalnum():
        raise ValueError(f"Value {param} does not match the ext format")
    return name, ext


class ExtParamInfo(ParamInfo):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        definition = self.raw_path[1:-1]
        parts = definition.split(":")
        self.ctx.allowed = []
        if len(parts) == 3:
            self.ctx.allowed = parts[2].split("|")
            if not all(ext.isalnum() for ext in self.ctx.allowed):
                raise InvalidUsage(
                    "Extensions may only be alphabetic characters"
                )
        elif len(parts) >= 3:
            raise InvalidUsage(f"Invalid ext definition: {self.raw_path}")

    def process(self, params, value):
        filename, ext = value
        if self.ctx.allowed and ext not in self.ctx.allowed:
            raise NotFound(f"Invalid extension: {ext}")
        params[self.name] = filename
        params["ext"] = ext


REGEX_PARAM_NAME = re.compile(r"^<([a-zA-Z_][a-zA-Z0-9_]*)(?::(.*))?>$")

# Predefined path parameter types. The value is a tuple consisteing of a
# callable and a compiled regular expression.
# The callable should:
#   1. accept a string input
#   2. cast the string to desired type
#   3. raise ValueError if it cannot
# The regular expression is generally NOT used. Unless the path is forced
# to use regex patterns.
REGEX_TYPES_ANNOTATION = Dict[
    str, Tuple[Callable[[str], Any], Pattern, Type[ParamInfo]]
]
REGEX_TYPES: REGEX_TYPES_ANNOTATION = {
    "string": (str, re.compile(r"^[^/]+$"), ParamInfo),
    "str": (str, re.compile(r"^[^/]+$"), ParamInfo),
    "ext": (ext, re.compile(r"^[^/]+$"), ExtParamInfo),
    "slug": (slug, re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$"), ParamInfo),
    "alpha": (alpha, re.compile(r"^[A-Za-z]+$"), ParamInfo),
    "path": (str, re.compile(r"^[^/]?.*?$"), ParamInfo),
    "number": (float, re.compile(r"^-?(?:\d+(?:\.\d*)?|\.\d+)$"), ParamInfo),
    "float": (float, re.compile(r"^-?(?:\d+(?:\.\d*)?|\.\d+)$"), ParamInfo),
    "int": (int, re.compile(r"^-?\d+$"), ParamInfo),
    "ymd": (
        parse_date,
        re.compile(r"^([12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))$"),
        ParamInfo,
    ),
    "uuid": (
        uuid.UUID,
        re.compile(
            r"^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-"
            r"[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$"
        ),
        ParamInfo,
    ),
}

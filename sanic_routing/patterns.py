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
    __slots__ = (
        "cast",
        "ctx",
        "label",
        "name",
        "pattern",
        "priority",
        "raw_path",
        "regex",
        "name_type",
        "ext_type",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        match = REGEX_PARAM_NAME_EXT.match(self.raw_path)
        self.name_type = match.group(2)
        self.ext_type = match.group(3)
        # definition = self.raw_path[1:-1]
        # parts = definition.split(":")
        regex_type = REGEX_TYPES.get(self.name_type)
        self.ctx.cast = None
        if regex_type:
            self.ctx.cast = regex_type[0]
        self.ctx.allowed = []
        if self.ext_type:
            self.ctx.allowed = self.ext_type.split("|")
            if not all(ext.isalnum() for ext in self.ctx.allowed):
                raise InvalidUsage(
                    "Extensions may only be alphabetic characters"
                )
        # elif len(parts) >= 3:
        #     raise InvalidUsage(f"Invalid ext definition: {self.raw_path}")

    def process(self, params, value):
        filename, ext = value
        if self.ctx.allowed and ext not in self.ctx.allowed:
            raise NotFound(f"Invalid extension: {ext}")
        if self.ctx.cast:
            try:
                filename = self.ctx.cast(filename)
            except ValueError:
                raise NotFound(f"Invalid filename: {filename}")
        params[self.name] = filename
        params["ext"] = ext


REGEX_PARAM_NAME = re.compile(r"^<([a-zA-Z_][a-zA-Z0-9_]*)(?::(.*))?>$")
REGEX_PARAM_NAME_EXT = re.compile(
    r"^<([a-zA-Z_][a-zA-Z0-9_]*)(?:=([a-z]+))?(?::ext(?:=([a-z|]+))?)>$"
)

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

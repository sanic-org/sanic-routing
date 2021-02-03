import typing as t
from collections import defaultdict, namedtuple
from types import SimpleNamespace

from .exceptions import InvalidUsage, RouteExists
from .patterns import REGEX_TYPES
from .utils import parts_to_path

# from sanic.exceptions import InvalidUsage


ParamInfo = namedtuple(
    "ParamInfo", ("name", "raw_path", "label", "cast", "pattern")
)


class Handler:
    # def __init__(self, func, requirements):
    #     self.mapping = {
    #         Requirements(requirements): func
    #     }
    # def add(self, func, requirements):
    #     self.mapping.update({
    #         Requirements(requirements): func
    #     })
    def __init__(self, func, requirements):
        self.handler_funcs = [(requirements, func)]

    def add(self, func, requirements):
        self.handler_funcs.append((requirements, func))

class Requirements(dict):
    def __hash__(self):
        return hash((frozenset(self), frozenset(self.values())))

class Route:
    def __init__(
        self, router, raw_path, name, strict: bool = False
    ):
        self.router = router
        self.name = name
        self.handlers = defaultdict(lambda: defaultdict(dict))
        self._params = defaultdict(list)
        self.raw_paths = set()
        self.ctx = SimpleNamespace()

        parts = tuple(raw_path.split(self.router.delimiter))
        self.path = parts_to_path(parts, delimiter=self.router.delimiter)
        self.parts = tuple(self.path.split(self.router.delimiter))
        self.static = "<" not in self.path
        self.strict: bool = strict

    def __repr__(self):
        display = (
            f"[{self.name}]{self.path or '/'}"
            if self.name and self.name != self.path
            else self.path or "/"
        )
        return f"<Route: {display}>"

    def get_handler(self, raw_path, method, **kwargs):
        method = method or self.router.DEFAULT_METHOD
        raw_path = raw_path.lstrip(self.router.delimiter)
        try:
            return self.handlers[raw_path][method]
        except KeyError:
            raise self.router.method_handler_exception(
                f"Method '{method}' not found on {self}",
                method=method,
                allowed_methods=set(self.handlers[raw_path].keys()),
            )

    def add_handler(self, raw_path, handler, method, requirements):
        # existing =self.handlers.get(raw_path, {})
        # if method in existing and Requirements(requirements) in existing[method]:
        #     req = f":{requirements}" if requirements else ""
        #     raise RouteExists(
        #         f"Route already registered: {raw_path} [{method}{req}]"
        #     )

        # self.handlers[raw_path][method.upper()][Requirements(requirements or {})] = Handler(handler, requirements)
        existing =self.handlers.get(raw_path, {})
        # TODO:
        # - Enable existing check
        # - check method and requirements
        # if method in existing:
        #     req = f":{requirements}" if requirements else ""
        #     raise RouteExists(
        #         f"Route already registered: {raw_path} [{method}{req}]"
        #     )

        if existing and existing[method.upper()]:
            existing[method.upper()].add(handler, requirements)
        else:
            self.handlers[raw_path][method.upper()] = Handler(handler, requirements)

        if not self.static:
            parts = tuple(raw_path.split(self.router.delimiter))
            for idx, part in enumerate(parts):
                if "<" in part:
                    if ":" in part:
                        (
                            name,
                            label,
                            _type,
                            pattern,
                        ) = self.parse_parameter_string(part[1:-1])
                        self.add_parameter(
                            idx, name, raw_path, label, _type, pattern
                        )
                    else:
                        self.add_parameter(
                            idx, part[1:-1], raw_path, "string", str, None
                        )

    def add_parameter(
        self,
        idx: int,
        name: str,
        raw_path: str,
        label: str,
        cast: t.Type,
        pattern=None,
    ):
        if label in self._params[idx]:
            raise RouteExists(f"{self} already has parameter defined at {idx}")

        self._params[idx].append(
            ParamInfo(name, raw_path, label, cast, pattern)
        )

    def finalize_params(self):
        self.params = {
            k: sorted(v, key=self._sorting, reverse=True)
            for k, v in self._params.items()
        }

    @staticmethod
    def _sorting(item) -> int:
        try:
            return list(REGEX_TYPES.keys()).index(item.label)
        except ValueError:
            raise InvalidUsage(f"Unknown path type: {item.label}")

    @staticmethod
    def parse_parameter_string(parameter_string: str):
        """Parse a parameter string into its constituent name, type, and
        pattern

        For example::

            parse_parameter_string('<param_one:[A-z]>')` ->
                ('param_one', '[A-z]', <class 'str'>, '[A-z]')

        :param parameter_string: String to parse
        :return: tuple containing
            (parameter_name, parameter_type, parameter_pattern)
        """
        # We could receive NAME or NAME:PATTERN
        name = parameter_string
        label = "string"
        if ":" in parameter_string:
            name, label = parameter_string.split(":", 1)
            if not name:
                raise ValueError(
                    f"Invalid parameter syntax: {parameter_string}"
                )

        default = (str, label)
        # Pull from pre-configured types
        _type, pattern = REGEX_TYPES.get(label, default)
        return name, label, _type, pattern

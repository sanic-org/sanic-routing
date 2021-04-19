import re
import typing as t
from collections import namedtuple
from types import SimpleNamespace

from .exceptions import InvalidUsage, ParameterNameConflicts
from .patterns import REGEX_TYPES
from .utils import Immutable, parts_to_path, path_to_parts

ParamInfo = namedtuple(
    "ParamInfo", ("name", "raw_path", "label", "cast", "pattern", "regex")
)


class Requirements(Immutable):
    def __hash__(self):
        return hash(frozenset(self.items()))


class Route:
    __slots__ = (
        "_params",
        "_raw_path",
        "ctx",
        "handler",
        "labels",
        "methods",
        "name",
        "overloaded",
        "params",
        "parts",
        "path",
        "pattern",
        "regex",
        "requirements",
        "router",
        "static",
        "strict",
        "unquote",
    )

    def __init__(
        self,
        router,
        raw_path: str,
        name: str,
        handler: t.Callable[..., t.Any],
        methods: t.Iterable[str],
        requirements: t.Dict[str, t.Any] = None,
        strict: bool = False,
        unquote: bool = False,
        static: bool = False,
        regex: bool = False,
        overloaded: bool = False,
    ):
        self.router = router
        self.name = name
        self.handler = handler
        self.methods = frozenset(methods)
        self.requirements = Requirements(requirements or {})

        self.ctx = SimpleNamespace()

        self._params: t.Dict[int, ParamInfo] = {}
        self._raw_path = raw_path

        parts = path_to_parts(raw_path, self.router.delimiter)
        self.path = parts_to_path(parts, delimiter=self.router.delimiter)
        self.parts = parts
        self.static = static
        self.regex = regex
        self.overloaded = overloaded
        self.pattern = None
        self.strict: bool = strict
        self.unquote: bool = unquote
        self.labels: t.Optional[t.List[str]] = None

        self._setup_params()

    def __str__(self):
        display = (
            f"name={self.name} path={self.path or self.router.delimiter}"
            if self.name and self.name != self.path
            else f"path={self.path or self.router.delimiter}"
        )
        return f"<{self.__class__.__name__}: {display}>"

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return bool(
            (
                self.parts,
                self.requirements,
            )
            == (
                other.parts,
                other.requirements,
            )
            and (self.methods & other.methods)
        )

    def _setup_params(self):
        key_path = parts_to_path(
            path_to_parts(self.raw_path, self.router.delimiter),
            self.router.delimiter,
        )
        if not self.static:
            parts = path_to_parts(key_path, self.router.delimiter)
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
                            idx, name, key_path, label, _type, pattern
                        )
                    else:
                        self.add_parameter(
                            idx, part[1:-1], key_path, "string", str, None
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
        if pattern and isinstance(pattern, str):
            if not pattern.startswith("^"):
                pattern = f"^{pattern}"
            if not pattern.endswith("$"):
                pattern = f"{pattern}$"

            pattern = re.compile(pattern)

        self._params[idx] = ParamInfo(
            name, raw_path, label, cast, pattern, label not in REGEX_TYPES
        )

    def _finalize_params(self):
        params = dict(self._params)
        label_pairs = set([(param.name, idx) for idx, param in params.items()])
        labels = [item[0] for item in label_pairs]
        if len(labels) != len(set(labels)):
            raise ParameterNameConflicts(
                f"Duplicate named parameters in: {self._raw_path}"
            )
        self.labels = labels
        self.params = dict(
            sorted(params.items(), key=lambda param: self._sorting(param[1]))
        )

    def _compile_regex(self):
        components = []

        for part in self.parts:
            if ":" in part:
                name, *_, pattern = self.parse_parameter_string(part)
                if not isinstance(pattern, str):
                    pattern = pattern.pattern.strip("^$")
                compiled = re.compile(pattern)
                if compiled.groups == 1:
                    if compiled.groupindex:
                        if list(compiled.groupindex)[0] != name:
                            raise InvalidUsage(
                                f"Named group ({list(compiled.groupindex)[0]})"
                                f" must match your named parameter ({name})"
                            )
                        components.append(pattern)
                    else:
                        if pattern.count("(") > 1:
                            raise InvalidUsage(
                                f"Could not compile pattern {pattern}. "
                                "Try using a named group instead: "
                                f"'(?P<{name}>your_matching_group)'"
                            )
                        beginning, end = pattern.split("(")
                        components.append(f"{beginning}(?P<{name}>{end}")
                elif compiled.groups > 1:
                    raise InvalidUsage(f"Invalid matching pattern {pattern}")
                else:
                    components.append(f"(?P<{name}>{pattern})")
            else:
                components.append(part)

        self.pattern = self.router.delimiter + self.router.delimiter.join(
            components
        )

    def finalize(self):
        self._finalize_params()
        if self.regex:
            self._compile_regex()
        self.requirements = Immutable(self.requirements)

    def reset(self):
        self.requirements = dict(self.requirements)

    @property
    def defined_params(self):
        return self._params

    @property
    def raw_path(self):
        return self._raw_path

    @staticmethod
    def _sorting(item) -> int:
        try:
            return list(REGEX_TYPES.keys()).index(item.label)
        except ValueError:
            return len(list(REGEX_TYPES.keys()))

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
        parameter_string = parameter_string.strip("<>")
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

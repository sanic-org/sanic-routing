import typing as t
from abc import ABC, abstractmethod
from itertools import count
from types import SimpleNamespace

from .exceptions import BadMethod, FinalizationError, NoMethod, NotFound
from .line import Line
from .patterns import REGEX_TYPES
from .route import Route
from .tree import Tree
from .utils import parts_to_path, path_to_parts

# The below functions might be called by the compiled source code, and
# therefore should be made available here by import
import re  # noqa  isort:skip
from datetime import datetime  # noqa  isort:skip
from urllib.parse import unquote  # noqa  isort:skip
from uuid import UUID  # noqa  isort:skip
from .patterns import parse_date  # noqa  isort:skip

TMP = count()


class BaseRouter(ABC):
    DEFAULT_METHOD = "BASE"
    ALLOWED_METHODS: t.Tuple[str, ...] = tuple()

    def __init__(
        self,
        delimiter: str = "/",
        exception: t.Type[NotFound] = NotFound,
        method_handler_exception: t.Type[NoMethod] = NoMethod,
        route_class: t.Type[Route] = Route,
        stacking: bool = False,
    ) -> None:
        self._find_route = None
        self.static_routes: t.Dict[t.Tuple[str, ...], Route] = {}
        self.dynamic_routes: t.Dict[t.Tuple[str, ...], Route] = {}
        self.regex_routes: t.Dict[t.Tuple[str, ...], Route] = {}
        self.name_index: t.Dict[str, Route] = {}
        self.delimiter = delimiter
        self.exception = exception
        self.method_handler_exception = method_handler_exception
        self.route_class = route_class
        self.tree = Tree()
        self.finalized = False
        self.stacking = stacking
        self.ctx = SimpleNamespace()

    @abstractmethod
    def get(self, **kwargs):
        ...

    def resolve(
        self,
        path: str,
        *,
        method: t.Optional[str] = None,
        orig: t.Optional[str] = None,
        extra: t.Optional[t.Dict[str, str]] = None,
    ):
        try:
            route, param_basket = self.find_route(
                path, self, {"__handler_idx__": 0, "__params__": {}}, extra
            )
        except NotFound as e:
            if path.endswith(self.delimiter):
                return self.resolve(
                    path=path[:-1],
                    method=method,
                    orig=path,
                    extra=extra,
                )
            raise self.exception(str(e), path=path)

        handler = None
        handler_idx = param_basket.pop("__handler_idx__")
        raw_path = param_basket.pop("__raw_path__")
        params = param_basket.pop("__params__")

        if route.strict and orig and orig[-1] != route.path[-1]:
            raise self.exception("Path not found", path=path)

        handler = route.get_handler(raw_path, method, handler_idx)

        return route, handler, params

    def add(
        self,
        path: str,
        handler: t.Callable,
        methods: t.Optional[t.Union[t.Iterable[str], str]] = None,
        name: t.Optional[str] = None,
        requirements: t.Optional[t.Dict[str, t.Any]] = None,
        strict: bool = False,
        unquote: bool = False,  # noqa
        overwrite: bool = False,
    ) -> Route:
        if not methods:
            methods = [self.DEFAULT_METHOD]

        if hasattr(methods, "__iter__") and not isinstance(methods, frozenset):
            methods = frozenset(methods)
        elif isinstance(methods, str):
            methods = frozenset([methods])

        if self.ALLOWED_METHODS and any(
            method not in self.ALLOWED_METHODS for method in methods
        ):
            bad = [
                method
                for method in methods
                if method not in self.ALLOWED_METHODS
            ]
            raise BadMethod(
                f"Bad method: {bad}. Must be one of: {self.ALLOWED_METHODS}"
            )

        if self.finalized:
            raise FinalizationError("Cannot finalize router more than once.")

        static = "<" not in path and not requirements
        regex = self._is_regex(path)

        if regex:
            routes = self.regex_routes
        elif static:
            routes = self.static_routes
        else:
            routes = self.dynamic_routes

        # Only URL encode the static parts of the path
        path = parts_to_path(
            path_to_parts(path, self.delimiter), self.delimiter
        )

        strip = path.lstrip if strict else path.strip
        path = strip(self.delimiter)
        route = self.route_class(
            self,
            path,
            name or "",
            strict=strict,
            unquote=unquote,
            static=static,
            regex=regex,
        )

        # Catch the scenario where a route is overloaded with and
        # and without requirements
        if static and route.parts in self.dynamic_routes:
            routes = self.dynamic_routes

        if route.parts in routes:
            route = routes[route.parts]
        else:
            routes[route.parts] = route

        if name:
            self.name_index[name] = route

        for method in methods:
            route.add_handler(path, handler, method, requirements)

        return route

    def finalize(self, do_compile: bool = True):
        if self.finalized:
            raise FinalizationError("Cannot finalize router more than once.")
        if not self.routes:
            raise FinalizationError("Cannot finalize with no routes defined.")
        self.finalized = True

        for route in self.routes.values():
            route.finalize()

        self._generate_tree()
        self._render(do_compile)

    def reset(self):
        self.finalized = False
        self.tree = Tree()
        self._find_route = None

        for route in self.routes.values():
            route.reset()

    def _generate_tree(self) -> None:
        self.tree.generate(self.dynamic_routes)
        self.tree.finalize()

    def _render(self, do_compile: bool = True) -> None:
        src = [
            Line("def find_route(path, router, basket, extra):", 0),
            Line("parts = tuple(path[1:].split(router.delimiter))", 1),
        ]

        if self.static_routes:
            # TODO:
            # - future improvement would be to decide which option to use
            #   at runtime based upon the makeup of the router since this
            #   potentially has an impact on performance
            src += [
                Line("try:", 1),
                Line("route = router.static_routes[parts]", 2),
                Line("basket['__raw_path__'] = path", 2),
                Line("return route, basket", 2),
                Line("except KeyError:", 1),
                Line("pass", 2),
            ]
            # src += [
            #     Line("if parts in router.static_routes:", 1),
            #     Line("route = router.static_routes[parts]", 2),
            #     Line("basket['__raw_path__'] = route.path", 2),
            #     Line("return route, basket", 2),
            # ]
            # src += [
            #     Line("if path in router.static_routes:", 1),
            #     Line("route = router.static_routes.get(path)", 2),
            #     Line("basket['__raw_path__'] = route.path", 2),
            #     Line("return route, basket", 2),
            # ]

        if self.dynamic_routes:
            src += [Line("num = len(parts)", 1)]
            src += self.tree.render()

        if self.regex_routes:
            # TODO:
            # - we should probably pre-compile the patterns and only
            #   include them here by reference
            src += [
                line
                for route in self.regex_routes.values()
                for line in [
                    Line(f"match = re.match(r'^{route.pattern}$', path)", 1),
                    Line("if match:", 1),
                    Line("basket['__params__'] = match.groupdict()", 2),
                    Line(f"basket['__raw_path__'] = '{route.path}'", 2),
                    Line(
                        f"return router.name_index['{route.name}'], basket", 2
                    ),
                ]
            ]

        self.optimize(src)

        self.find_route_src = "".join(
            map(str, filter(lambda x: x.render, src))
        )
        if do_compile:
            compiled_src = compile(
                self.find_route_src,
                "",
                "exec",
            )
            ctx: t.Dict[t.Any, t.Any] = {}
            exec(compiled_src, None, ctx)
            self._find_route = ctx["find_route"]

    @property
    def find_route(self):
        return self._find_route

    @property
    def routes(self):
        return {
            **self.static_routes,
            **self.dynamic_routes,
            **self.regex_routes,
        }

    @staticmethod
    def optimize(src: t.List[Line]) -> None:
        """
        Insert NotFound exceptions to be able to bail as quick as possible,
        and realign lines to proper indentation
        """
        offset = 0
        current = 0
        insert_at = set()
        for num, line in enumerate(src):
            if line.indent < current:
                if not line.src.startswith("."):
                    offset = 0

            if (
                line.src.startswith("if")
                or line.src.startswith("elif")
                or line.src.startswith("return")
                or line.src.startswith("basket")
            ):

                idnt = line.indent + 1
                prev_line = src[num - 1]
                while idnt < prev_line.indent:
                    insert_at.add((num, idnt))
                    idnt += 1

            offset += line.offset
            line.indent += offset
            current = line.indent

        idnt = 1
        prev_line = src[-1]
        while idnt < prev_line.indent:
            insert_at.add((len(src), idnt))
            idnt += 1

        for num, indent in sorted(insert_at, key=lambda x: (x[0] * -1, x[1])):

            next(TMP)
            src.insert(num, Line("raise NotFound", indent))

    def _is_regex(self, path: str):
        parts = path_to_parts(path, self.delimiter)

        def requires(part):
            if not part.startswith("<") or ":" not in part:
                return False

            _, pattern_type = part[1:-1].split(":", 1)

            return (
                part.endswith(":path>")
                or self.delimiter in part
                or pattern_type not in REGEX_TYPES
            )

        return any(requires(part) for part in parts)

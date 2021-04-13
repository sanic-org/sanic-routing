from .exceptions import InvalidUsage, RouteExists


class RouteGroup:
    def __init__(self, *routes) -> None:
        if len(set(route.parts for route in routes)) > 1:
            raise InvalidUsage("Cannout group routes with differing paths")

        if any(routes[-1].strict != route.strict for route in routes):
            raise InvalidUsage(
                "Cannout group routes with differing strictness"
            )

        route_list = list(routes)
        route_list.pop()

        self._routes = routes
        self._method_index = {
            method: route
            for route in route_list
            for method in route.defined_methods
        }
        self.pattern_idx = 0

    def __str__(self):
        display = (
            f"path={self.path or self.router.delimiter} len={len(self.routes)}"
        )
        return f"<{self.__class__.__name__}: {display}>"

    def __iter__(self):
        return iter(self.routes)

    def __getitem__(self, key):
        return self.routes[key]

    def merge(self, group, overwrite: bool = False):
        _routes = list(self._routes)
        for other_route in group.routes:
            for current_route in self:
                if current_route == other_route:
                    if not overwrite:
                        raise RouteExists(
                            f"Route already registered: {self.raw_path} "
                            f"[{','.join(self.methods)}]"
                        )
                else:
                    _routes.append(other_route)
        self._routes = tuple(_routes)

    @property
    def labels(self):
        return self[0].labels

    @property
    def methods(self):
        return frozenset(
            [method for route in self for method in route.methods]
        )

    @property
    def params(self):
        return self[0].params

    @property
    def parts(self):
        return self[0].parts

    @property
    def path(self):
        return self[0].path

    @property
    def pattern(self):
        return self[0].pattern

    @property
    def raw_path(self):
        return self[0].raw_path

    @property
    def regex(self):
        return self[0].regex

    @property
    def requirements(self):
        return [route.requirements for route in self if route.requirements]

    @property
    def routes(self):
        return self._routes

    @property
    def router(self):
        return self[0].router

    @property
    def strict(self):
        return self[0].strict

    @property
    def unquote(self):
        return self[0].unquote

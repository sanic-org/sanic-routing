import pytest
from sanic_routing import BaseRouter
from sanic_routing.exceptions import RouteExists


class Router(BaseRouter):
    def get(self, path, method):
        return self.resolve(path=path, method=method)


def test_add_route():
    router = Router()
    router.add("/foo/bar", lambda *args, **kwargs: ...)

    assert len(router.static_routes) == 1

    route = list(router.static_routes.values())[0]
    assert route.parts == ("foo", "bar")


def test_alternatice_delimiter():
    router = Router(delimiter=":")
    router.add("foo:bar", lambda *args, **kwargs: ...)

    assert len(router.static_routes) == 1

    route = list(router.static_routes.values())[0]
    assert route.parts == ("foo", "bar")


def test_add_duplicate_route_fails():
    router = Router()

    router.add("/foo/bar", lambda *args, **kwargs: ...)
    with pytest.raises(RouteExists):
        router.add("/foo/bar", lambda *args, **kwargs: ...)

    router.add("/foo/<bar>", lambda *args, **kwargs: ...)
    with pytest.raises(RouteExists):
        router.add("/foo/<bar>", lambda *args, **kwargs: ...)


def test_add_duplicate_route_alt_method():
    router = Router()
    router.add("/foo/bar", lambda *args, **kwargs: ...)
    router.add("/foo/bar", lambda *args, **kwargs: ..., methods=["ALT"])
    router.add("/foo/<bar>", lambda *args, **kwargs: ...)
    router.add("/foo/<bar:int>", lambda *args, **kwargs: ...)

    assert len(router.static_routes) == 1
    assert len(router.dynamic_routes) == 1

    static_handlers = list(
        list(router.static_routes.values())[0].handlers.values()
    )
    assert len(static_handlers[0]) == 2

    dynamic_handlers = list(
        list(router.dynamic_routes.values())[0].handlers.values()
    )
    assert len(dynamic_handlers[0]) == 1
    assert len(dynamic_handlers[1]) == 1


def test_cast_types():
    def handler(bar):
        return bar

    router = Router()
    router.add("/foo/<bar>", handler)
    router.add("/foo/<bar:int>", handler)

    router.finalize()
    router.tree.display()
    print(router.find_route_src)

    string_bar = router.get("/foo/something", "BASE")
    int_bar = router.get("/foo/111", "BASE")

    string_retval = string_bar[1](**string_bar[2])
    assert isinstance(string_retval, str)
    assert string_retval == "something"

    int_retval = int_bar[1](**int_bar[2])
    assert isinstance(int_retval, int)
    assert int_retval == 111

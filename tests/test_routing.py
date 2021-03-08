import uuid
from datetime import date

import pytest
from sanic_routing import BaseRouter
from sanic_routing.exceptions import NoMethod, NotFound, RouteExists


@pytest.fixture
def handler():
    def handler(**kwargs):
        return list(kwargs.values())[0]

    return handler


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
    router.add("/foo/bar", lambda *args, **kwargs: ..., overwrite=True)

    router.add("/foo/<bar>", lambda *args, **kwargs: ...)
    with pytest.raises(RouteExists):
        router.add("/foo/<bar>", lambda *args, **kwargs: ...)
    router.add("/foo/<bar>", lambda *args, **kwargs: ..., overwrite=True)


def test_add_duplicate_route_alt_method():
    router = Router()
    router.add("/foo/bar", lambda *args, **kwargs: ...)
    router.add("/foo/bar", lambda *args, **kwargs: ..., methods=["ALT"])
    router.add("/foo/<bar>", lambda *args, **kwargs: ...)
    router.add("/foo/<bar:int>", lambda *args, **kwargs: ...)

    assert len(router.static_routes) == 1
    assert len(router.dynamic_routes) == 2

    static_handlers = list(
        list(router.static_routes.values())[0].handlers.values()
    )
    assert len(static_handlers[0]) == 2

    for route in router.dynamic_routes.values():
        assert len(list(route.handlers.values())) == 1
        assert len(list(route.handlers.values())) == 1


def test_route_does_not_exist():
    router = Router()
    router.add("/foo", handler)
    router.finalize()

    with pytest.raises(NotFound):
        router.get("/path/to/nothing", "BASE")


def test_method_does_not_exist():
    router = Router()
    router.add("/foo", handler)
    router.finalize()

    with pytest.raises(NoMethod):
        router.get("/foo", "XXXXXXX")


def test_cast_types_at_same_position(handler):
    router = Router()
    router.add("/foo/<bar>", handler)
    router.add("/foo/<bar:int>", handler)

    router.finalize()

    string_bar = router.get("/foo/something", "BASE")
    int_bar = router.get("/foo/111", "BASE")

    string_retval = string_bar[1](**string_bar[2])
    assert isinstance(string_retval, str)
    assert string_retval == "something"

    int_retval = int_bar[1](**int_bar[2])
    assert isinstance(int_retval, int)
    assert int_retval == 111


@pytest.mark.parametrize(
    "label,value,cast_type",
    (
        ("string", "foo", str),
        ("int", 11111, int),
        ("number", 99.99, float),
        ("alpha", "ABCxyz", str),
        ("ymd", "2021-01-01", date),
        ("uuid", uuid.uuid4(), uuid.UUID),
    ),
)
def test_casting(handler, label, value, cast_type):
    router = Router()
    router.add(f"/<foo:{label}>", handler)

    router.finalize()
    _, handler, params = router.get(f"/{value}", "BASE")
    retval = handler(**params)

    assert isinstance(retval, cast_type)


def test_conditional_check_proper_compile(handler):
    router = Router()
    router.add("/<foo>/", handler, strict=True)
    router.add("/<foo>/", handler, strict=True, requirements={"foo": "bar"})
    router.finalize()

    assert router.finalized

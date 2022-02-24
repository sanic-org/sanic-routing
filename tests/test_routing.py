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
    def get(self, path, method, extra=None):
        return self.resolve(path=path, method=method, extra=extra)


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
    assert len(router.routes) == 1
    with pytest.raises(RouteExists):
        router.add("/foo/bar", lambda *args, **kwargs: ...)
    router.add("/foo/bar", lambda *args, **kwargs: ..., overwrite=True)
    assert len(router.routes) == 1

    router.add("/foo/<bar>", lambda *args, **kwargs: ...)
    assert len(router.routes) == 2
    with pytest.raises(RouteExists):
        router.add("/foo/<bar>", lambda *args, **kwargs: ...)
    router.add("/foo/<bar>", lambda *args, **kwargs: ..., overwrite=True)
    assert len(router.routes) == 2


def test_add_duplicate_route_alt_method():
    router = Router()
    router.add("/foo/bar", lambda *args, **kwargs: ...)
    router.add("/foo/bar", lambda *args, **kwargs: ..., methods=["ALT"])
    router.add("/foo/<bar>", lambda *args, **kwargs: ...)
    router.add("/foo/<bar:int>", lambda *args, **kwargs: ...)

    assert len(router.static_routes) == 1
    assert len(router.dynamic_routes) == 2

    static_handlers = list(router.static_routes.values())[0]
    assert len(static_handlers.routes) == 2

    for group in router.dynamic_routes.values():
        assert len(group.routes) == 1
        assert len(group.routes) == 1


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
        ("str", "foo_-", str),
        ("int", 11111, int),
        ("alpha", "ABCxyz", str),
        ("ymd", "2021-01-01", date),
        ("uuid", uuid.uuid4(), uuid.UUID),
        ("slug", "foo-bar", str),
    ),
)
def test_casting(handler, label, value, cast_type):
    router = Router()
    router.add("/<str:str>", handler)
    router.add("/<int:int>", handler)
    router.add("/<alpha:alpha>", handler)
    router.add("/<ymd:ymd>", handler)
    router.add("/<uuid:uuid>", handler)
    router.add("/<slug:slug>", handler)

    router.finalize()
    _, handler, params = router.get(f"/{value}", "BASE")
    retval = handler(**params)

    assert isinstance(retval, cast_type)
    assert label in params


def test_conditional_check_proper_compile(handler):
    router = Router()
    router.add("/<foo>/", handler, strict=True)

    with pytest.raises(RouteExists):
        router.add(
            "/<foo>/", handler, strict=True, requirements={"foo": "bar"}
        )
    router.finalize()

    assert router.finalized


@pytest.mark.parametrize(
    "param_name",
    (
        "fooBar",
        "foo_bar",
        "Foobar",
        "foobar1",
    ),
)
def test_use_param_name(handler, param_name):
    router = Router()
    path_part_with_param = f"<{param_name}>"
    path_part_with_param_as_string = f"<{param_name}:str>"
    router.add(f"/path/{path_part_with_param}", handler)
    route = list(router.routes)[0]
    assert ("path", path_part_with_param_as_string) == route.parts


@pytest.mark.parametrize(
    "param_name",
    (
        "fooBar",
        "foo_bar",
        "Foobar",
        "foobar1",
    ),
)
def test_use_param_name_with_casing(handler, param_name):
    router = Router()
    path_part_with_param = f"<{param_name}:str>"
    router.add(f"/path/{path_part_with_param}", handler)
    route = list(router.routes)[0]
    assert ("path", path_part_with_param) == route.parts


def test_use_route_contains_children(handler):
    router = Router()
    router.add("/foo/<foo_id>/bars_ids", handler)
    router.add(
        "/foo/<foo_id>/bars_ids/<bar_id>/settings/<group_id>/groups", handler
    )

    router.finalize()

    bars_ids = router.get("/foo/123/bars_ids", "BASE")
    bars_ids_groups = router.get(
        "/foo/123/bars_ids/321/settings/111/groups", "BASE"
    )

    bars_ids_retval = bars_ids[1](**bars_ids[2])
    assert isinstance(bars_ids_retval, str)
    assert bars_ids_retval == "123"

    bars_ids_group_dict = bars_ids_groups[2]
    assert bars_ids_group_dict == {
        "foo_id": "123",
        "bar_id": "321",
        "group_id": "111",
    }


def test_use_route_with_different_depth(handler):
    router = Router()
    router.add("/foo/<foo_id>", handler)
    router.add("/foo/<foo_id>/settings", handler)
    router.add("/foo/<foo_id>/bars/<bar_id>/settings", handler)
    router.add("/foo/<foo_id>/bars_ids", handler)
    router.add("/foo/<foo_id>/bars_ids/<bar_id>/settings", handler)
    router.add(
        "/foo/<foo_id>/bars_ids/<bar_id>/settings/<group_id>/groups", handler
    )

    router.finalize()

    router.get("/foo/123", "BASE")
    router.get("/foo/123/settings", "BASE")
    router.get("/foo/123/bars/321/settings", "BASE")
    router.get("/foo/123/bars_ids", "BASE")
    router.get("/foo/123/bars_ids/321/settings", "BASE")
    router.get("/foo/123/bars_ids/321/settings/111/groups", "BASE")


def test_use_route_type_coercion(handler):
    router = Router()
    router.add("/test/<foo:int>", handler)
    router.add("/test/<foo:int>/bar", handler)

    router.finalize()

    router.get("/test/123", "BASE")
    router.get("/test/123/bar", "BASE")

    with pytest.raises(NotFound):
        router.get("/test/foo/aaaa", "BASE")
    with pytest.raises(NotFound):
        router.get("/test/123/aaaa", "BASE")
    with pytest.raises(NotFound):
        router.get("/test/123/aaaa/bbbb", "BASE")


def test_use_route_type_coercion_deeper(handler):
    router = Router()
    router.add("/test/<foo:int>", handler)
    router.add("/test/<foo:int>/bar", handler)
    router.add("/test/<foo:int>/bar/baz", handler)

    router.finalize()

    router.get("/test/123", "BASE")
    router.get("/test/123/bar", "BASE")
    router.get("/test/123/bar/baz", "BASE")

    with pytest.raises(NotFound):
        router.get("/test/foo/aaaa", "BASE")
    with pytest.raises(NotFound):
        router.get("/test/123/aaaa", "BASE")
    with pytest.raises(NotFound):
        router.get("/test/123/aaaa/bbbb", "BASE")
    with pytest.raises(NotFound):
        router.get("/test/123/aaaa/bbbb/cccc", "BASE")
    with pytest.raises(NotFound):
        router.get("/test/foo/bar", "BASE")
    with pytest.raises(NotFound):
        router.get("/test/123/bar/bbbb", "BASE")
    with pytest.raises(NotFound):
        router.get("/test/123/bar/bbbb/cccc", "BASE")


def test_route_correct_coercion():
    def handler1():
        ...

    def handler2():
        ...

    def handler3():
        ...

    def handler4():
        ...

    router = Router()
    router.add("/<test:str>", handler1)
    router.add("/<test:int>", handler2)
    router.add("/<test:uuid>", handler3)
    router.add("/<test:ymd>", handler4)

    router.finalize()

    _, h1, __ = router.get("/foo", "BASE")
    _, h2, __ = router.get("/123", "BASE")
    _, h3, __ = router.get("/726a7d33-4bd5-46a3-a02d-37da7b4b029b", "BASE")
    _, h4, __ = router.get("/2021-03-21", "BASE")

    assert h1 is handler1
    assert h2 is handler2
    assert h3 is handler3
    assert h4 is handler4


def test_non_strict_bail_out():
    def handler1():
        return "handler1"

    def handler2():
        return "handler2"

    def handler3():
        return "handler3"

    router = Router()
    router.add("/test", handler1, requirements={"req": "foo"})
    router.add("/test", handler2, requirements={"req": "bar"})
    router.add("/test/ing", handler3, requirements={"req": "bar"})

    router.finalize()

    _, handler, __ = router.get("/test", "BASE", extra={"req": "foo"})
    assert handler() == "handler1"

    _, handler, __ = router.get("/test/", "BASE", extra={"req": "foo"})
    assert handler() == "handler1"

    _, handler, __ = router.get("/test", "BASE", extra={"req": "bar"})
    assert handler() == "handler2"

    _, handler, __ = router.get("/test/", "BASE", extra={"req": "bar"})
    assert handler() == "handler2"

    _, handler, __ = router.get("/test/ing", "BASE", extra={"req": "bar"})
    assert handler() == "handler3"

    _, handler, __ = router.get("/test/ing/", "BASE", extra={"req": "bar"})
    assert handler() == "handler3"


def test_non_strict_with_params():
    def handler1():
        return "handler1"

    def handler2():
        return "handler2"

    router = Router()
    router.add("/<foo>", handler1)
    router.add("/<foo>/ing", handler2)

    router.finalize()

    _, handler, params = router.get("/test", "BASE")
    assert handler() == "handler1"
    assert params == {"foo": "test"}

    _, handler, params = router.get("/test/", "BASE")
    assert handler() == "handler1"
    assert params == {"foo": "test"}

    _, handler, params = router.get("/test/ing", "BASE")
    assert handler() == "handler2"
    assert params == {"foo": "test"}

    _, handler, params = router.get("/test/ing/", "BASE")
    assert handler() == "handler2"
    assert params == {"foo": "test"}


def test_path_with_paamayim_nekudotayim():
    def handler(**kwargs):
        return kwargs

    router = Router()
    router.add(
        r"/path/to/<file_uuid:(?P<file_uuid>[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}"
        r"-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})(?:\.[A-z]{1,4})?>",
        handler,
    )

    router.finalize()

    _, handler, params = router.get(
        "/path/to/726a7d33-4bd5-46a3-a02d-37da7b4b029b.jpeg", "BASE"
    )
    assert handler(**params) == params
    assert params == {"file_uuid": "726a7d33-4bd5-46a3-a02d-37da7b4b029b"}


def test_multiple_handlers_on_final_regex_segment(handler):
    def handler1():
        return "handler1"

    def handler2():
        return "handler2"

    router = Router()
    router.add("/path/to/<foo:bar>", handler1, methods=("one", "two"))
    router.add("/path/to/<foo:bar>", handler2, methods=("three",))
    router.add("/path/<to>/distraction", handler)
    router.add("/path/<to>", handler)
    router.add("/path", handler)
    router.add("/somehwere/<else>", handler)

    router.finalize()

    _, handler, params = router.get("/path/to/bar", "one")
    assert handler() == "handler1"
    assert params == {"foo": "bar"}

    _, handler, params = router.get("/path/to/bar", "two")
    assert handler() == "handler1"
    assert params == {"foo": "bar"}

    _, handler, params = router.get("/path/to/bar", "three")
    assert handler() == "handler2"
    assert params == {"foo": "bar"}


@pytest.mark.parametrize("uri", ("a-random-path", "a/random/path"))
def test_identical_path_routes_with_different_methods_simple(uri):
    def handler1():
        return "handler1"

    def handler2():
        return "handler2"

    # test root level path with different methods
    router = Router()
    router.add("/<foo:path>", handler1, methods=["GET", "OPTIONS"])
    router.add("/<foo:path>", handler2, methods=["POST"])
    router.finalize()

    _, handler, params = router.get(f"/{uri}", "POST")
    assert handler() == "handler2"
    assert params == {"foo": f"{uri}"}

    _, handler, params = router.get(f"/{uri}", "GET")
    assert handler() == "handler1"
    assert params == {"foo": f"{uri}"}


@pytest.mark.parametrize(
    "uri",
    (
        "a-random-path",
        "a/random/path",
    ),
)
def test_identical_path_routes_with_different_methods_complex(uri):
    def handler1():
        return "handler1"

    def handler2():
        return "handler2"

    router = Router()
    router.add("/<foo:path>", handler1, methods=["OPTIONS"])
    router.add("/api/<version:int>/hello_world", handler2, methods=["POST"])
    router.add(
        "/api/<version:int>/hello_world/<foo:path>", handler2, methods=["GET"]
    )
    router.finalize()

    _, handler, params = router.get(f"/{uri}", "OPTIONS")
    assert handler() == "handler1"
    assert params == {"foo": uri}

    _, handler, params = router.get("/api/3/hello_world", "POST")
    assert handler() == "handler2"
    assert params == {"version": 3}

    _, handler, params = router.get(f"/api/3/hello_world/{uri}", "GET")
    assert handler() == "handler2"
    assert params == {"version": 3, "foo": uri}


@pytest.mark.parametrize("uri", ("a-random-path", "a/random/path"))
def test_identical_path_routes_with_different_methods_similar_urls(uri):
    def handler1():
        return "handler1"

    def handler2():
        return "handler2"

    def handler3():
        return "handler3"

    # test root level path with different methods
    router = Router()
    router.add(
        "/constant/<foo:path>/story", handler1, methods=["GET", "OPTIONS"]
    )
    router.add(
        "/constant/<foo:path>/tracker/events", handler2, methods=["PUT"]
    )
    router.add(
        "/constant/<foo:path>/tracker/events", handler3, methods=["POST"]
    )
    router.finalize()

    route, handler, params = router.get(f"/constant/{uri}/story", "GET")
    assert params == {"foo": f"{uri}"}
    assert handler() == "handler1"

    _, handler, params = router.get(f"/constant/{uri}/tracker/events", "PUT")
    assert params == {"foo": f"{uri}"}
    assert handler() == "handler2"

    _, handler, params = router.get(f"/constant/{uri}/tracker/events", "POST")
    assert params == {"foo": f"{uri}"}
    assert handler() == "handler3"

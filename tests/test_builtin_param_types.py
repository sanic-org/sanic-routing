import pytest
from sanic_routing import BaseRouter
from sanic_routing.exceptions import NotFound


@pytest.fixture
def handler():
    def handler(**kwargs):
        return list(kwargs.values())[0]

    return handler


class Router(BaseRouter):
    def get(self, path, method, extra=None):
        return self.resolve(path=path, method=method, extra=extra)


def test_alpha_does_cast(handler):
    router = Router()

    router.add("/<alphaonly:alpha>", handler)
    router.finalize()

    _, handler, params = router.get("/foobar", "BASE")
    retval = handler(**params)

    assert isinstance(retval, str)
    assert retval == "foobar"


def test_alpha_does_not_cast(handler):
    router = Router()

    router.add("/<alphaonly:alpha>", handler)
    router.finalize()

    with pytest.raises(NotFound):
        router.get("/notfound123", "BASE")


def test_correct_alpha_v_string(handler):
    router = Router()

    router.add("/<alphaonly:alpha>", handler, methods=["alpha"])
    router.add("/<anystring:str>", handler, methods=["str"])
    router.finalize()

    _, handler, params = router.get("/foobar", "alpha")
    retval = handler(**params)

    assert isinstance(retval, str)
    assert retval == "foobar"

    _, handler, params = router.get("/foobar123", "str")
    retval = handler(**params)

    assert isinstance(retval, str)
    assert retval == "foobar123"


def test_use_string_raises_deprecation_warning(handler):
    router = Router()

    with pytest.warns(DeprecationWarning) as record:
        router.add("/<foo:string>", handler)

    assert len(record) == 1
    assert record[0].message.args[0] == (
        "Use of 'string' as a path parameter type is deprected, and will be "
        "removed in Sanic v21.12. Instead, use <foo:str>."
    )


@pytest.mark.parametrize(
    "value", ("foo-bar", "foobar", "foo-bar-thing123", "foobar123", "123")
)
def test_slug_does_cast(handler, value):
    router = Router()

    router.add("/<slug:slug>", handler)
    router.finalize()

    _, handler, params = router.get(f"/{value}", "BASE")
    retval = handler(**params)

    assert isinstance(retval, str)
    assert retval == value


@pytest.mark.parametrize("value", ("-aaa", "FooBar", "Foo-Bar"))
def test_slug_does_not_cast(handler, value):
    router = Router()

    router.add("/<slug:slug>", handler)
    router.finalize()

    with pytest.raises(NotFound):
        router.get(f"/{value}", "BASE")


def test_correct_slug_v_string(handler):
    router = Router()

    router.add("/<slug:slug>", handler, methods=["slug"])
    router.add("/<anystring:str>", handler, methods=["str"])
    router.finalize()

    _, handler, params = router.get("/foo-bar", "slug")
    retval = handler(**params)

    assert isinstance(retval, str)
    assert retval == "foo-bar"

    _, handler, params = router.get("/FooBar", "str")
    retval = handler(**params)

    assert isinstance(retval, str)
    assert retval == "FooBar"

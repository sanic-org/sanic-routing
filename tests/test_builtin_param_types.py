import pytest
from sanic_routing import BaseRouter
from sanic_routing.exceptions import InvalidUsage, NotFound


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


def test_use_number_raises_deprecation_warning(handler):
    router = Router()

    with pytest.warns(DeprecationWarning) as record:
        router.add("/<foo:number>", handler)

    assert len(record) == 1
    assert record[0].message.args[0] == (
        "Use of 'number' as a path parameter type is deprected, and will be "
        "removed in Sanic v21.12. Instead, use <foo:float>."
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


@pytest.mark.parametrize(
    "value", ("somefile.txt", "SomeFile.mp3", "some.thing", "with.extra.dot")
)
def test_ext_not_defined_matches(value):
    def handler(**kwargs):
        return kwargs

    router = Router()

    router.add("/<filename:ext>", handler)
    router.finalize()

    _, handler, params = router.get(f"/{value}", "BASE")
    retval = handler(**params)

    filename, ext = value.rsplit(".", 1)
    assert retval["filename"] == filename
    assert retval["ext"] == ext


@pytest.mark.parametrize("value", ("somefile.mp3", "with.extra.mp3"))
def test_ext_single_defined_matches(value):
    def handler(**kwargs):
        return kwargs

    router = Router()

    router.add("/<filename:ext:mp3>", handler)
    router.finalize()

    _, handler, params = router.get(f"/{value}", "BASE")
    retval = handler(**params)

    filename, ext = value.rsplit(".", 1)
    assert retval["filename"] == filename
    assert retval["ext"] == ext


@pytest.mark.parametrize(
    "value",
    ("somefile.png", "with.extra.png", "somefile.jpg", "with.extra.jpg"),
)
def test_ext_multiple_defined_matches(value):
    def handler(**kwargs):
        return kwargs

    router = Router()

    router.add("/<filename:ext:jpg|png|gif>", handler)
    router.finalize()

    _, handler, params = router.get(f"/{value}", "BASE")
    retval = handler(**params)

    filename, ext = value.rsplit(".", 1)
    assert retval["filename"] == filename
    assert retval["ext"] == ext


@pytest.mark.parametrize(
    "value",
    ("somefile", "SomeFile."),
)
def test_ext_not_defined_no_matches(handler, value):
    def handler(**kwargs):
        return kwargs

    router = Router()

    router.add("/<filename:ext>", handler)
    router.finalize()

    with pytest.raises(NotFound):
        router.get(f"/{value}", "BASE")


@pytest.mark.parametrize(
    "value",
    ("somefile", "SomeFile.", "somefile.jpg"),
)
def test_ext_single_defined_no_matches(handler, value):
    def handler(**kwargs):
        return kwargs

    router = Router()

    router.add("/<filename:ext:txt>", handler)
    router.finalize()

    with pytest.raises(NotFound):
        router.get(f"/{value}", "BASE")


@pytest.mark.parametrize(
    "value",
    ("somefile", "SomeFile.", "somefile.txt"),
)
def test_ext_multiple_defined_no_matches(handler, value):
    def handler(**kwargs):
        return kwargs

    router = Router()

    router.add("/<filename:ext:jpg|png|gif>", handler)
    router.finalize()

    with pytest.raises(NotFound):
        router.get(f"/{value}", "BASE")


@pytest.mark.parametrize(
    "definition",
    (
        "<filename:ext:and:more>",
        "<filename:ext:bad#>",
    ),
)
def test_bad_ext_definition(handler, definition):
    router = Router()

    with pytest.raises(InvalidUsage):
        router.add(f"/{definition}", handler)

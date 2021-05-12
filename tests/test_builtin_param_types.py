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

    router.add("/<alphaonly:alpha>", handler)
    router.add("/<anystring:string>", handler)
    router.finalize()

    _, handler, params = router.get("/foobar", "BASE")
    retval = handler(**params)

    assert isinstance(retval, str)
    assert retval == "foobar"

    _, handler, params = router.get("/foobar123", "BASE")
    retval = handler(**params)

    assert isinstance(retval, str)
    assert retval == "foobar123"

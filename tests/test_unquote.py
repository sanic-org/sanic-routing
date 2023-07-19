from unittest.mock import Mock

from sanic_routing import BaseRouter


class Router(BaseRouter):
    def get(self, path, method, extra=None):
        return self.resolve(path=path, method=method, extra=extra)


def test_no_unquote():
    handler = Mock(return_value=123)

    router = Router()
    router.add("/<foo>/<bar>", methods=["GET"], handler=handler, unquote=False)
    router.finalize()

    _, handler, params = router.get("/%F0%9F%98%8E/sunglasses", "GET")
    assert params == {"bar": "sunglasses", "foo": "%F0%9F%98%8E"}

    _, handler, params = router.get("/😎/sunglasses", "GET")
    assert params == {"bar": "sunglasses", "foo": "😎"}


def test_unquote():
    handler = Mock(return_value=123)

    router = Router()
    router.add("/<foo>/<bar>", methods=["GET"], handler=handler, unquote=True)
    router.finalize()

    _, handler, params = router.get("/%F0%9F%98%8E/sunglasses", "GET")
    assert params == {"bar": "sunglasses", "foo": "😎"}

    _, handler, params = router.get("/😎/sunglasses", "GET")
    assert params == {"bar": "sunglasses", "foo": "😎"}


def test_unquote_non_string():
    handler = Mock(return_value=123)

    router = Router()
    router.add(
        "/<foo>/<bar:int>", methods=["GET"], handler=handler, unquote=True
    )
    router.finalize()

    _, handler, params = router.get("/%F0%9F%98%8E/123", "GET")
    assert params == {"bar": 123, "foo": "😎"}

    _, handler, params = router.get("/😎/123", "GET")
    assert params == {"bar": 123, "foo": "😎"}

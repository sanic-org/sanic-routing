import pytest

from sanic_routing import BaseRouter


class Router(BaseRouter):
    def get(self, path, method):
        return self.resolve(path=path, method=method)


@pytest.mark.parametrize(
    "cascade,lines,not_founds",
    (
        (True, 25, 1),
        (False, 25, 1),
    ),
)
def test_route_correct_coercion(cascade, lines, not_founds):
    def handler():
        ...

    router = Router(cascade_not_found=cascade)
    router.add("/<one>", handler)
    router.add("/<one>/two/three", handler)

    router.finalize()

    assert router.find_route_src.count("\n") == lines
    assert router.find_route_src.count("raise NotFound") == not_founds

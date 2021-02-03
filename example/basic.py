from dataclasses import dataclass, field
from functools import partial
from typing import Optional

from sanic_routing import BaseRouter
from sanic_routing.route import Route


@dataclass
class FakeRequest:
    path: str
    method: str
    route: Optional[Route] = field(default=None)

    def __hash__(self) -> int:
        return hash(f"{self.method} {self.path}")


class Router(BaseRouter):
    DEFAULT_METHOD = "GET"
    ALLOWED_METHODS = (
        "GET",
        "POST",
        "PUT",
        "HEAD",
        "OPTIONS",
        "PATCH",
        "DELETE",
    )

    def get(self, request: FakeRequest):
        return self.resolve(request.path, method=request.method)


def handler(*args, **kwargs):
    print("~~This is the handler~~")
    print(f"\t{args=}")
    print(f"\t{kwargs=}")


router = Router()
routes = [
    "/foo/bar",
    "/<foo>/bar",
    "/<foo:int>/bar",
    "/foo/<bar:uuid>",
    "/foo/<bar:ymd>",
]

for i, r in enumerate(routes):
    router.add(r, partial(handler, i))

router.finalize()
router.tree.display()
print(router.find_route_src)
print(f"{router.static_routes=}")
print(f"{router.dynamic_routes=}")
request = FakeRequest("/foo/2021-01-01", "POST")
route, handler, params = router.get(request)
request.route = route
args = (request,)
print(f"{route=}")
print(f"{handler=}")
print(f"{args=}")
print(f"{params=}")
handler(*args, **params)

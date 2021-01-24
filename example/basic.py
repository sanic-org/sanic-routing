from functools import partial

from sanic_routing import BaseRouter


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

    def get(self, path, *args, **kwargs):
        return self.resolve(path, *args, **kwargs)


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
route, handler, args, params = router.get("/foo/2021-01-01")
print(f"{route=}")
print(f"{handler=}")
print(f"{args=}")
print(f"{params=}")
handler(*args, **params)

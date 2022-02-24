import ipaddress
import re

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


def test_does_cast(handler):
    router = Router()
    router.register_pattern(
        "ipv4",
        ipaddress.ip_address,
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|"
        r"2[0-4][0-9]|[01]?[0-9][0-9]?)$",
    )

    router.add("/<ip:ipv4>", handler)
    router.finalize()

    _, handler, params = router.get("/1.2.3.4", "BASE")
    retval = handler(**params)

    assert isinstance(retval, ipaddress.IPv4Address)


def test_does_not_cast(handler):
    router = Router()
    router.register_pattern(
        "ipv4",
        ipaddress.ip_address,
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|"
        r"2[0-4][0-9]|[01]?[0-9][0-9]?)$",
    )

    router.add("/<ip:ipv4>", handler)
    router.finalize()

    with pytest.raises(NotFound):
        router.get("/notfound", "BASE")


def test_works_with_patterns(handler):
    router = Router()
    router.register_pattern(
        "ipv4",
        ipaddress.ip_address,
        re.compile(
            r"^(?:(?:25[0-5]|2[0-4][0-9]|"
            r"[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|"
            r"2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        ),
    )

    router.add("/<ip:ipv4>", handler)
    router.finalize()

    with pytest.raises(NotFound):
        router.get("/notfound", "BASE")


def test_bad_registries():
    router = Router()

    with pytest.raises(InvalidUsage):
        router.register_pattern(None, None, None)

    with pytest.raises(InvalidUsage):
        router.register_pattern("ipv4", None, None)

    with pytest.raises(InvalidUsage):
        router.register_pattern("ipv4", ipaddress.ip_address, None)

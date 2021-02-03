from typing import Optional, Set


class BaseException(Exception):
    ...


class NotFound(BaseException):
    def __init__(
        self,
        message,
        path: Optional[str] = None,
    ):
        super().__init__(message)
        self.path = path


class NoMethod(BaseException):
    def __init__(
        self,
        message,
        method: Optional[str] = None,
        allowed_methods: Optional[Set[str]] = None,
    ):
        super().__init__(message)
        self.method = method
        self.allowed_methods = allowed_methods

class InvalidUsage(BaseException):
    ...

class RouteExists(BaseException):
    ...

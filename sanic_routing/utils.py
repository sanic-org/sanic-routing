import re
from typing import TYPE_CHECKING, Any, Dict, List, NoReturn, Tuple
from urllib.parse import quote, unquote

from sanic_routing.exceptions import InvalidUsage

from .patterns import REGEX_PARAM_NAME, REGEX_PARAM_NAME_EXT

if TYPE_CHECKING:
    from .route import Route


class Immutable(Dict[str, str]):
    def __setitem__(self, *args: Any) -> NoReturn:
        raise TypeError("Cannot change immutable dict")

    def __delitem__(self, *args: Any) -> NoReturn:
        raise TypeError("Cannot change immutable dict")


def parse_parameter_basket(
    route: "Route", basket: Dict[int, Any], raw_path=None
):
    params = {}
    if basket:
        for idx, value in basket.items():
            for p in route.params[idx]:
                if not raw_path or p.raw_path == raw_path:
                    if not p.regex:
                        raw_path = p.raw_path
                        params[p.name] = p.cast(value)
                        break
                    elif p.pattern.search(value):
                        raw_path = p.raw_path
                        if "(" in p.pattern:
                            groups = p.pattern.match(value)
                            value = groups.group(1)
                        params[p.name] = p.cast(value)
                        break

                    if raw_path:
                        raise ValueError("Invalid parameter")

                if raw_path and not params[p.name]:
                    raise ValueError("Invalid parameter")

            if route.unquote:
                for p in route.params[idx]:
                    if isinstance(params[p.name], str):
                        params[p.name] = unquote(params[p.name])

    if raw_path is None:
        raise ValueError("Invalid parameter")
    return params, raw_path


def path_to_parts(path: str, delimiter: str = "/") -> tuple[str, ...]:
    r"""
    OK > /foo/<id:int>/bar/<name:[A-z]+>
    OK > /foo/<unhashable:[A-Za-z0-9/]+>
    OK > /foo/<ext:file\.(?P<ext>txt)>/<ext:[a-z]>
    OK > /foo/<user>/<user:str>
    OK > /foo/<ext:[a-z]>/<ext:file\.(?P<ext>txt)d>
    NOT OK > /foo/<ext:file\.(?P<ext>txt)d>/<ext:[a-z]>
    """
    path = unquote(path.lstrip(delimiter))
    delimiter = re.escape(delimiter)
    return tuple(
        part if part.startswith("<") else quote(part)
        for part in re.split(rf"{delimiter}(?=[^>]*(?:<(?<!\?<)|$))", path)
    )


def parts_to_path(parts: Tuple[str, ...], delimiter: str = "/"):
    path: List[str] = []
    for part in parts:
        if part.startswith("<"):
            match = REGEX_PARAM_NAME.match(part)
            param_type = ""
            if match:
                if match.group(2):
                    param_type = f":{match.group(2)}"
                path.append(f"<{match.group(1)}{param_type}>")
            else:
                match = REGEX_PARAM_NAME_EXT.match(part)
                filename_type = ""
                extension_type = ""
                if match:
                    if match.group(2):
                        filename_type = f"={match.group(2)}"
                    if match.group(3):
                        extension_type = f"={match.group(3)}"
                    segment = (
                        f"<{match.group(1)}{filename_type}:"
                        f"ext{extension_type}>"
                    )
                    path.append(segment)
                else:
                    raise InvalidUsage(f"Invalid declaration: {part}")
        else:
            path.append(part)
    return delimiter.join(path)

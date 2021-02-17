import re
from urllib.parse import quote, unquote

from .patterns import REGEX_PARAM_NAME


class Immutable(dict):
    def __setitem__(self, *args):
        raise TypeError("Cannot change immutable dict")

    def __delitem__(self, *args):
        raise TypeError("Cannot change immutable dict")


def parse_parameter_basket(route, basket, raw_path=None):
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


def path_to_parts(path, delimiter="/"):
    """
    OK > /foo/<id:int>/bar/<name:[A-z]+>
    OK > /foo/<unhashable:[A-Za-z0-9/]+>
    OK > /foo/<ext:file\.(?P<ext>txt)>/<ext:[a-z]>  # noqa
    OK > /foo/<user>/<user:str>
    OK > /foo/<ext:[a-z]>/<ext:file\.(?P<ext>txt)d>  # noqa
    NOT OK > /foo/<ext:file\.(?P<ext>txt)d>/<ext:[a-z]>  # noqa
    """
    regex_path_parts = re.compile(
        f"(<[a-z\:]+?>|<.*?(?<![a-z])>|[^{delimiter}]+)"  # noqa
    )
    parts = list(regex_path_parts.findall(unquote(path))) or [""]
    if path.endswith(delimiter):
        parts += [""]
    return tuple(
        [part if part.startswith("<") else quote(part) for part in parts]
    )


def parts_to_path(parts, delimiter="/"):
    path = []
    for part in parts:
        if part.startswith("<"):
            try:
                match = REGEX_PARAM_NAME.match(part)
                param_type = ""
                if match.group(2):
                    param_type = f":{match.group(2)}"
                path.append(f"<{match.group(1)}{param_type}>")
            except AttributeError:
                raise ValueError(f"Invalid declaration: {part}")
        else:
            path.append(part)
    return delimiter.join(path)

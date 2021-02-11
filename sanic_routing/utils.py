import re
from urllib.parse import quote, unquote

from .patterns import REGEX_PARAM_NAME


def parse_parameter_basket(route, basket, raw_path=None):
    params = {}
    if basket:
        for idx, value in basket.items():
            for p in route.params[idx]:
                # print(params, raw_path)
                # print(f"[{idx}] >> {p} for {value=}")
                if not raw_path or p.raw_path == raw_path:
                    if not p.regex:
                        raw_path = p.raw_path
                        params[p.name] = p.cast(value)
                        break
                    elif p.pattern.search(value):
                        raw_path = p.raw_path
                        params[p.name] = p.cast(value)
                        break

                    if raw_path:
                        raise ValueError("1...")

                if raw_path and not params[p.name]:
                    raise ValueError("2...")

            if route.unquote:
                for p in route.params[idx]:
                    if isinstance(params[p.name], str):
                        params[p.name] = unquote(params[p.name])

    if raw_path is None:
        raise ValueError("3...")
    return params, raw_path


def path_to_parts(path, delimiter="/"):
    regex_path_parts = re.compile(f"(<.*?>|[^{delimiter}]+)")
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

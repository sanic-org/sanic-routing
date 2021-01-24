from .patterns import REGEX_PARAM_NAME


def parse_parameter_basket(route, basket):
    params = {}
    raw_path = None
    if basket:
        for idx, value in basket.items():
            for p in route.params[idx]:
                if not raw_path or p.raw_path == raw_path:
                    if not p.pattern:
                        raw_path = p.raw_path
                        params[p.name] = str(value)
                        break
                    elif p.pattern.search(value):
                        raw_path = p.raw_path
                        params[p.name] = p.cast(value)
                        break

                    if raw_path:
                        raise Exception("1...")

                if raw_path and not params[p.name]:
                    raise Exception("2...")
    return params, raw_path


def parts_to_path(parts):
    path = []
    for part in parts:
        if part.startswith("<"):
            match = REGEX_PARAM_NAME.match(part)
            path.append(f"<{match.group(1)}>")
        else:
            path.append(part)
    return "/".join(path)

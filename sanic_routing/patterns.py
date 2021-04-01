import re
import uuid
from datetime import datetime


def parse_date(d):
    return datetime.strptime(d, "%Y-%m-%d").date()


REGEX_PARAM_NAME = re.compile(r"^<([a-zA-Z_][a-zA-Z0-9_]*)(?::(.*))?>$")
REGEX_TYPES = {
    "string": (str, re.compile(r"^[^/]+")),
    "alpha": (str, re.compile(r"^[A-Za-z]+")),
    "path": (str, re.compile(r"^[^/]?.*?")),
    "number": (float, re.compile(r"^-?(?:\d+(?:\.\d*)?|\.\d+)")),
    "int": (int, re.compile(r"^-?\d+")),
    "ymd": (
        parse_date,
        re.compile(r"^([12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))"),
    ),
    "uuid": (
        uuid.UUID,
        re.compile(
            r"^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-"
            r"[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}"
        ),
    ),
}

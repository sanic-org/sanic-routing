import pytest

from sanic_routing.utils import path_to_parts


@pytest.mark.parametrize(
    "parts",
    (
        ("",),
        ("foo",),
        ("foo", "<user>", "<user:str>", ""),
        ("foo", "<id:int>", "bar", r"<name:[A-z]+>"),
        ("foo", r"<unhashable:[A-Za-z0-9/]+>"),
        ("foo", r"<ext:file\.(?P<ext>txt)>", r"<ext:[a-z]>"),
        ("foo", r"<ext:[a-z]>", r"<ext:file\.(?P<ext>txt)d>"),
        ("iiif", "<img_id>", r"<region:full|square|\d+,\d+,\d+,\d+>",
         r"<size:max|\d+,|,\d+|\d+,\d+>", "<rotation:int>", "default.jpg"),
        ("test", "<rest:a(?>bc|b)c>", ""),
        ("test", "<rest:[a-z]{10}/extra)?>"),
        ("path", "to", r"<deeply_nested:[a-z/]+>", "thing"),
    )
)
def test_path_to_parts_splitter(parts):
    path = "/".join(parts)
    assert path_to_parts(f"/{path}") == parts, path


@pytest.mark.parametrize(
    "parts",
    (
        ("foo",),
        ("foo", "bar", "baz"),
        ("<foo>", "bar", "baz"),
        ("foo", "<bar>", "baz"),
        ("foo", "<bar>", "<baz:int>"),
        ("foo", "<bar:An.*>"),
        ("foo", "<b:Ar.*>", "<b:Az.*>"),
        ("foo", "<id:int>", "bar", r"<name:[A-z]+>"),
        ("foo", r"<unhashable:[A-Za-z0-9/]+>"),
        ("iiif", "<img_id>", r"<region:full|square|\d+\.\d+\.\d+\.\d+>",
         r"<size:max|\d+\.|\.\d+|\d+\.\d+>", "<rotation:int>", "default"),
        ("test", "<rest:a(?>bc|b)c>"),
        ("test", r"<rest:[a-z]{10}extra\..+)?>", "<fest>"),
    )
)
def test_path_to_parts_splitter_dot_delimiter(parts):
    path = ".".join(parts)
    assert path_to_parts(path, delimiter=".") == parts, path


@pytest.mark.parametrize(
    "path,parts",
    (
        ("no/start/slash/", ("no", "start", "slash", "")),
        ("/%E4%BD%A0%E5%A5%BD/hello", ("%E4%BD%A0%E5%A5%BD", "hello")),
        ("/πάτι/ᴄᴏᴅᴇ", ("%CF%80%CE%AC%CF%84%CE%B9", "%E1%B4%84%E1%B4%8F%E1%B4%85%E1%B4%87")),
        ("/юзер/<user>/<name:str>/", ("%D1%8E%D0%B7%D0%B5%D1%80", "<user>", "<name:str>", "")),
        (r"/ru/<ext:файл\.(?P<ext>txt)>/<ext:[a-z]>", ("ru", "<ext:файл\.(?P<ext>txt)>", "<ext:[a-z]>")),
    )
)
def test_path_to_parts_splitter_normalization(path, parts):
    assert path_to_parts(path) == parts, path

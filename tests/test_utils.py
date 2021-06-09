import pytest

from sanic_routing.utils import path_to_parts


@pytest.mark.parametrize(
    "path,parts",
    (
        (
            r"/foo/<user>/<user:str>/",
            ("foo", "<user>", "<user:str>", "")
         ),
        (
            r"/foo/<id:int>/bar/<name:[A-z]+>",
            ("foo", "<id:int>", "bar", r"<name:[A-z]+>")
        ),
        (
            r"/foo/<unhashable:[A-Za-z0-9/]+>",
            ("foo", r"<unhashable:[A-Za-z0-9/]+>")
        ),
        (
            r"/foo/<ext:file\.(?P<ext>txt)>/<ext:[a-z]>",
            ("foo", r"<ext:file\.(?P<ext>txt)>", r"<ext:[a-z]>")
        ),
        (
            r"/foo/<ext:[a-z]>/<ext:file\.(?P<ext>txt)d>",
            ("foo", r"<ext:[a-z]>", r"<ext:file\.(?P<ext>txt)d>")
        ),
        (
            r"/iiif/<img_id>/<region:full|square|\d+,\d+,\d+,\d+>/"
            r"<size:max|\d+,|,\d+|\d+,\d+>/<rotation:int>/default.jpg",
            ("iiif", "<img_id>", r"<region:full|square|\d+,\d+,\d+,\d+>",
             r"<size:max|\d+,|,\d+|\d+,\d+>", "<rotation:int>", "default.jpg")
        ),
        (
            r"/test/<rest:a(?>bc|b)c>/",
            ("test", "<rest:a(?>bc|b)c>", "")
        ),
        (
            r"/test/<rest:[a-z]{10}/extra)?>",
            ("test", "<rest:[a-z]{10}/extra)?>")
        ),
        (
            r"/path/to/<deeply_nested:[a-z/]+>/thing",
            ("path", "to", r"<deeply_nested:[a-z/]+>", "thing")
        ),
    ),
)
def test_path_to_parts_splitter(path, parts):
    assert path_to_parts(path) == parts

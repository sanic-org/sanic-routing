"""
Sanic
"""
import codecs
import os
import re

from setuptools import setup


def open_local(paths, mode="r", encoding="utf8"):
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), *paths)

    return codecs.open(path, mode, encoding)


with open_local(["sanic_routing", "__init__.py"], encoding="latin1") as fp:
    try:
        version = re.findall(
            r"^__version__ = \"([^']+)\"\r?$", fp.read(), re.M
        )[0]
    except IndexError:
        raise RuntimeError("Unable to determine version.")

with open_local(["README.md"]) as rm:
    long_description = rm.read()

setup_kwargs = {
    "name": "sanic-routing",
    "version": version,
    "url": "https://github.com/sanic-org/sanic-routing/",
    "license": "MIT",
    "author": "Adam Hopkins",
    "author_email": "admhpkns@gmail.com",
    "description": ("Core routing component for Sanic"),
    "long_description": long_description,
    "long_description_content_type": "text/markdown",
    "packages": ["sanic_routing"],
    "platforms": "any",
    "classifiers": [
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
}
requirements = []

tests_require = ["pytest", "sanic", "pytest-asyncio"]

setup_kwargs["install_requires"] = None
setup_kwargs["tests_require"] = tests_require
setup(**setup_kwargs)

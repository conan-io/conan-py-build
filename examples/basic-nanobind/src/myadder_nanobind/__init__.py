from importlib.metadata import version

from myadder_nanobind._core import add, add_integers, greet

__version__ = version("myadder-nanobind")
__all__ = ["add", "add_integers", "greet"]

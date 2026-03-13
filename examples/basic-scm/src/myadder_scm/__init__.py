from myadder_scm._core import add, add_integers, greet

try:
    from myadder_scm._version import __version__
except ImportError:
    __version__ = "0.0.0"

__all__ = ["add", "add_integers", "greet"]

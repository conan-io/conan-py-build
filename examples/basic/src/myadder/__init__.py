from importlib.metadata import version

from myadder._core import add, add_integers, greet

# Read from the installed wheel metadata, so the version lives only in pyproject.toml.
__version__ = version("myadder")
__all__ = ["add", "add_integers", "greet"]

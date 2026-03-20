"""
conan-py-build: A minimal PEP 517 compliant build backend that uses Conan
to build Python C/C++ extensions.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    # Canonical version lives in pyproject.toml [project].version
    __version__ = version("conan-py-build")
except PackageNotFoundError:
    __version__ = "0.0.0"

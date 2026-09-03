from importlib.metadata import version

from myxslt_cibw._core import transform, libxml2_version, libxslt_version

__version__ = version("myxslt-cibw")
__all__ = ["transform", "libxml2_version", "libxslt_version"]

try:
    # _version.py is written by setuptools-scm
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

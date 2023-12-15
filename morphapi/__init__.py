from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("morphapi")
except PackageNotFoundError:
    # package is not installed
    pass

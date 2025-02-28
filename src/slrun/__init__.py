"""Tools for running commands on SLURM as if local."""

from importlib.metadata import version, PackageNotFoundError
try:
    __version__ = version("slrun")
except PackageNotFoundError:
    __version__ = "dev"

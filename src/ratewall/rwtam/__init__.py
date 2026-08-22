"""A monthly structural-accounting model of monetary-policy transmission through selected financial claims and fiscal channels."""

from ratewall.rwtam.engine import RwtamResult, run_rwtam
from ratewall.rwtam.schemas import RwtamConfig, RwtamConfigError, load_config

__all__ = [
    "RwtamConfig",
    "RwtamConfigError",
    "RwtamResult",
    "load_config",
    "run_rwtam",
]

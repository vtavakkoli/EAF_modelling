"""EAF model Python package."""

from .config import EAFConfig
from .simulation.core import run_simulation

__all__ = ["EAFConfig", "run_simulation"]

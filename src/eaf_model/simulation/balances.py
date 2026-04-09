from __future__ import annotations

import math

from eaf_model.simulation.state import EAFState


def validate_state(state: EAFState) -> None:
    vals = state.__dict__.values()
    if any((not math.isfinite(v)) for v in vals):
        raise ValueError("Non-finite state detected")

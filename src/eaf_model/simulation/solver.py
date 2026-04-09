from __future__ import annotations

from eaf_model.config import EAFConfig
from eaf_model.simulation.balances import validate_state
from eaf_model.simulation.chemistry import compute_reaction_rates
from eaf_model.simulation.heat_transfer import update_temperatures
from eaf_model.simulation.mass_transfer import update_mass
from eaf_model.simulation.state import EAFState


def euler_step(state: EAFState, cfg: EAFConfig, dt: float) -> None:
    rates = compute_reaction_rates(state, cfg.o2_lance_kg_s)
    update_mass(state, rates, cfg, dt)
    update_temperatures(state, cfg, dt)
    validate_state(state)

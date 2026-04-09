from __future__ import annotations

from eaf_model.config import EAFConfig
from eaf_model.simulation.state import EAFState


def update_temperatures(state: EAFState, cfg: EAFConfig, dt: float) -> None:
    power_kw = cfg.arc_power_kw
    heat_capacity_liquid = max(state.m_fe_lsc + state.m_c_lsc + state.m_mn_lsc, 1.0) * 0.75
    heat_capacity_slag = max(state.m_liquid_slag_total, 1.0) * 0.9

    d_t_lsc = (power_kw * 0.55 - 0.08 * (state.t_lsc - state.t_gas)) / heat_capacity_liquid
    d_t_lsl = (power_kw * 0.25 - 0.06 * (state.t_lsl - state.t_gas)) / heat_capacity_slag
    d_t_gas = (power_kw * 0.10 + 0.03 * (state.t_lsc - state.t_gas) + 0.03 * (state.t_lsl - state.t_gas) - 40.0)
    d_t_gas /= max(state.m_co + state.m_co2 + state.m_o2, 1.0)

    state.t_lsc += d_t_lsc * dt
    state.t_lsl += d_t_lsl * dt
    state.t_gas += d_t_gas * dt

    state.t_lsc = max(300.0, min(3500.0, state.t_lsc))
    state.t_lsl = max(300.0, min(3500.0, state.t_lsl))
    state.t_gas = max(300.0, min(3500.0, state.t_gas))

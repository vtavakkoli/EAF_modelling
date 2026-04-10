from __future__ import annotations

from dataclasses import asdict
from typing import Any

from eaf_model.config import EAFConfig
from eaf_model.constants import MOLAR_MASS
from eaf_model.simulation.geometry import derive_geometry
from eaf_model.simulation.solver import euler_step
from eaf_model.simulation.state import EAFState


Timeseries = list[dict[str, float]]


def run_simulation(config: EAFConfig) -> tuple[Timeseries, dict[str, Any]]:
    state = EAFState()
    records: Timeseries = []
    takeout_every = max(int(config.takeout_interval_s / config.time_step_s), 1)

    for idx in range(config.steps + 1):
        t = idx * config.time_step_s
        if idx % max(int(1.0 / config.time_step_s), 1) == 0:
            total_gas = max(state.m_co + state.m_co2, 1e-9)
            records.append(
                {
                    "time_s": t,
                    "t_liquid_metal_k": state.t_lsc,
                    "t_liquid_slag_k": state.t_lsl,
                    "t_gas_k": state.t_gas,
                    "m_liquid_metal_kg": state.m_fe_lsc + state.m_c_lsc + state.m_mn_lsc,
                    "m_solid_kg": state.m_solid_total,
                    "m_liquid_slag_kg": state.m_liquid_slag_total,
                    "m_fe_lsc_kg": state.m_fe_lsc,
                    "m_feo_lsl_kg": state.m_feo_lsl,
                    "co2_to_co_ratio": state.m_co2 / max(state.m_co, 1e-9),
                    "carbon_wt_pct": 100.0 * state.m_c_lsc / max(state.m_fe_lsc + state.m_c_lsc + state.m_mn_lsc, 1e-9),
                    "manganese_wt_pct": 100.0 * state.m_mn_lsc / max(state.m_fe_lsc + state.m_c_lsc + state.m_mn_lsc, 1e-9),
                    "offgas_carbon_oxides_kg": total_gas,
                    "selectivity_fe": (state.m_fe_lsc / MOLAR_MASS.FE) / max(state.m_feo_lsl / MOLAR_MASS.FEO, 1e-9),
                }
            )

        if idx > 0:
            euler_step(state, config, config.time_step_s)

        if idx > 0 and idx % takeout_every == 0:
            state.m_fe_lsc *= 0.5
            state.m_c_lsc *= 0.5
            state.m_mn_lsc *= 0.5
            state.m_liquid_slag_total *= 0.5

    final = records[-1]
    geom = derive_geometry(config.geometry)
    summary = {
        "config": asdict(config),
        "final": final,
        "kpi": {
            "reactor_volume_m3": geom.volume_m3,
            "arc_power_mw": config.arc_power_kw / 1000.0,
            "oxygen_total_kg_s": config.o2_lance_kg_s + config.o2_post_kg_s,
            "co2_to_co_ratio": float(final["co2_to_co_ratio"]),
            "liquid_metal_temperature_k": float(final["t_liquid_metal_k"]),
        },
    }
    return records, summary

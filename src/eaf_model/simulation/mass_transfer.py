from __future__ import annotations

from eaf_model.config import EAFConfig
from eaf_model.constants import MOLAR_MASS
from eaf_model.simulation.chemistry import ReactionRates
from eaf_model.simulation.state import EAFState


def update_mass(state: EAFState, rates: ReactionRates, cfg: EAFConfig, dt: float) -> None:
    # Portion of injected carbon dissolves into liquid steel, remainder is available as injected carbon.
    dissolved_c = 0.35 * cfg.c_inj_kg_s * dt
    injected_c = cfg.c_inj_kg_s * dt - dissolved_c
    state.m_c_lsc += dissolved_c
    state.m_injected_c += injected_c

    # Ferro-manganese injection composition (legacy MATLAB mass fractions).
    state.m_mn_lsc += cfg.fm_inj_kg_s * 0.78 * dt
    state.m_c_lsc += cfg.fm_inj_kg_s * 0.07 * dt
    state.m_fe_lsc += cfg.fm_inj_kg_s * 0.145 * dt

    # FeO + C -> Fe + CO (injected and dissolved C)
    r_feo_cl = min(rates.r_feo_cl, state.m_injected_c / max(MOLAR_MASS.C * dt, 1e-12))
    r_feo_cd = min(rates.r_feo_cd, state.m_c_lsc / max(MOLAR_MASS.C * dt, 1e-12))

    for r in (r_feo_cl, r_feo_cd):
        state.m_feo_lsl -= r * MOLAR_MASS.FEO * dt
        state.m_fe_lsc += r * MOLAR_MASS.FE * dt
        state.m_co += r * MOLAR_MASS.CO * dt

    state.m_injected_c -= r_feo_cl * MOLAR_MASS.C * dt
    state.m_c_lsc -= r_feo_cd * MOLAR_MASS.C * dt

    # C + O2 -> CO2
    state.m_c_lsc -= rates.r_c_o2 * MOLAR_MASS.C * dt
    state.m_co2 += rates.r_c_o2 * MOLAR_MASS.CO2 * dt
    state.m_o2 -= rates.r_c_o2 * MOLAR_MASS.O2 * dt

    # MnO + C -> Mn + CO
    state.m_mno_lsl -= rates.r_mno_c * MOLAR_MASS.MNO * dt
    state.m_c_lsc -= rates.r_mno_c * MOLAR_MASS.C * dt
    state.m_mn_lsc += rates.r_mno_c * MOLAR_MASS.MN * dt
    state.m_co += rates.r_mno_c * MOLAR_MASS.CO * dt

    # Feeds
    state.m_solid_total += (cfg.dri_add_kg_s + cfg.scrap_add_kg_s) * dt
    state.m_liquid_slag_total += cfg.slag_add_kg_s * dt
    state.m_o2 += (cfg.o2_lance_kg_s + cfg.o2_post_kg_s) * dt

    # Offgas venting proxy
    vent_coeff = 0.022
    state.m_co = max(1e-8, state.m_co - vent_coeff * state.m_co * dt)
    state.m_co2 = max(1e-8, state.m_co2 - vent_coeff * state.m_co2 * dt)
    state.m_o2 = max(1e-8, state.m_o2 - vent_coeff * state.m_o2 * dt)

    # Physical constraints
    for attr in ("m_feo_lsl", "m_c_lsc", "m_mno_lsl", "m_fe_lsc", "m_mn_lsc", "m_solid_total", "m_liquid_slag_total", "m_injected_c"):
        setattr(state, attr, max(0.0, getattr(state, attr)))

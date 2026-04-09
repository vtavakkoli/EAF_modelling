from __future__ import annotations

from dataclasses import dataclass

from eaf_model.constants import KINETICS, MOLAR_MASS
from eaf_model.simulation.state import EAFState


@dataclass
class ReactionRates:
    r_feo_cl: float
    r_feo_cd: float
    r_c_o2: float
    r_mno_c: float


def compute_reaction_rates(state: EAFState, o2_lance_kg_s: float) -> ReactionRates:
    m_liq = max(state.m_fe_lsc + state.m_c_lsc + state.m_mn_lsc, 1e-9)
    x_c = state.m_c_lsc / m_liq
    x_feo = state.m_feo_lsl / max(state.m_liquid_slag_total, 1e-9)
    x_mno = state.m_mno_lsl / max(state.m_liquid_slag_total, 1e-9)

    r_feo_cl = max(0.0, state.m_injected_c * KINETICS.KD_CL * x_feo / MOLAR_MASS.C)
    r_feo_cd = max(0.0, KINETICS.KD_CD * max(0.0, x_c - 0.0015) / MOLAR_MASS.C)
    r_c_o2 = min(
        max(0.0, KINETICS.KD_C_O2 * max(0.0, x_c - 0.0015) * o2_lance_kg_s / MOLAR_MASS.C),
        o2_lance_kg_s / MOLAR_MASS.C,
    )
    r_mno_c = max(0.0, KINETICS.KD_MNO_C * max(0.0, x_mno - 0.02) / MOLAR_MASS.MNO)
    return ReactionRates(r_feo_cl=r_feo_cl, r_feo_cd=r_feo_cd, r_c_o2=r_c_o2, r_mno_c=r_mno_c)

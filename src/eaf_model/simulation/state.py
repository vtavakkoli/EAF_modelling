from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EAFState:
    # Main tracked masses (kg)
    m_fe_lsc: float = 64411.0
    m_c_lsc: float = 314.0
    m_mn_lsc: float = 617.0
    m_feo_lsl: float = 3195.0
    m_mno_lsl: float = 960.0
    m_solid_total: float = 1334.1
    m_liquid_slag_total: float = 11568.49

    m_co: float = 1388.0
    m_co2: float = 190.0
    m_o2: float = 414.0

    # Temperatures (K)
    t_lsc: float = 2079.0
    t_lsl: float = 1997.0
    t_gas: float = 1854.0

    m_injected_c: float = 0.792

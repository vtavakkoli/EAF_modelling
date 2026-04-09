from __future__ import annotations

import math
from dataclasses import dataclass

from eaf_model.config import GeometryConfig


@dataclass
class GeometryDerived:
    bath_area_m2: float
    upper_area_m2: float
    volume_m3: float


def derive_geometry(cfg: GeometryConfig) -> GeometryDerived:
    bath = math.pi * cfg.r_eafin_m**2
    upper = math.pi * cfg.r_eafout_m**2
    volume = upper * cfg.h_eafup_m + bath * cfg.h_eaflow_m
    return GeometryDerived(bath_area_m2=bath, upper_area_m2=upper, volume_m3=volume)

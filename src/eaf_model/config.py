from __future__ import annotations

"""Configuration models for all workflows."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GeometryConfig:
    r_eafout_m: float = 3.3
    r_eafin_m: float = 2.45
    h_eafup_m: float = 2.9
    h_eaflow_m: float = 1.0


@dataclass
class EAFConfig:
    time_step_s: float = 0.01
    total_time_s: float = 120.0
    takeout_interval_s: float = 60.0

    dri_add_kg_s: float = 346656 / 3600
    scrap_add_kg_s: float = 80000 / 3600
    slag_add_kg_s: float = 3.0

    c_inj_kg_s: float = 0.3
    fm_inj_kg_s: float = 1.5
    o2_lance_kg_s: float = 4.0
    o2_post_kg_s: float = 1.0
    arc_power_kw: float = 40000.0

    t_dri_k: float = 559.32
    t_scrap_k: float = 559.32
    t_slag_k: float = 300.0

    geometry: GeometryConfig = field(default_factory=GeometryConfig)

    @property
    def steps(self) -> int:
        return int(self.total_time_s / self.time_step_s)


@dataclass
class RunMetadata:
    workflow: str
    output_dir: Path
    timestamp_utc: str
    python_version: str

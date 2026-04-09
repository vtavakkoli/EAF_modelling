from eaf_model.config import EAFConfig
from eaf_model.simulation.core import run_simulation


def test_simulation_non_empty() -> None:
    rows, summary = run_simulation(EAFConfig(total_time_s=10.0, time_step_s=0.02))
    assert len(rows) > 0
    assert summary["final"]["t_liquid_metal_k"] > 0
    assert rows[-1]["m_liquid_metal_kg"] > 0

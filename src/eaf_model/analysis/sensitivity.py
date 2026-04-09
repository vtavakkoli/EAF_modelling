from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from eaf_model.config import EAFConfig
from eaf_model.io.results import make_run_dir, write_dataframe, write_summary
from eaf_model.plotting.plots import plot_simulation
from eaf_model.simulation.core import run_simulation

SENSITIVITY_CASES = {
    "carbon_injection": ("c_inj_kg_s", [0.8, 0.9, 1.0, 1.1, 1.2]),
    "ferromn_injection": ("fm_inj_kg_s", [0.8, 0.9, 1.0, 1.1, 1.2]),
    "oxygen_lance": ("o2_lance_kg_s", [0.8, 0.9, 1.0, 1.1, 1.2]),
    "oxygen_post": ("o2_post_kg_s", [0.8, 0.9, 1.0, 1.1, 1.2]),
    "slag_forming": ("slag_add_kg_s", [0.8, 0.9, 1.0, 1.1, 1.2]),
    "takeout": ("takeout_interval_s", [0.8, 0.9, 1.0, 1.1, 1.2]),
    "arcpower": ("arc_power_kw", [0.8, 0.9, 1.0, 1.1, 1.2]),
}


def run_sensitivity(base_cfg: EAFConfig, output_root: Path, make_plots: bool = True) -> tuple[Path, list[dict[str, float | str]]]:
    run_dir = make_run_dir(output_root, "sensitivity")
    rows: list[dict[str, float | str]] = []

    for case_name, (field_name, multipliers) in SENSITIVITY_CASES.items():
        original_value = getattr(base_cfg, field_name)
        for mult in multipliers:
            cfg = replace(base_cfg, **{field_name: original_value * mult})
            ts_rows, summary = run_simulation(cfg)
            row = {
                "case": case_name,
                "parameter": field_name,
                "multiplier": mult,
                "carbon_wt_pct": summary["final"]["carbon_wt_pct"],
                "manganese_wt_pct": summary["final"]["manganese_wt_pct"],
                "liquid_temp_k": summary["final"]["t_liquid_metal_k"],
                "co2_to_co_ratio": summary["final"]["co2_to_co_ratio"],
                "offgas_carbon_oxides_kg": summary["final"]["offgas_carbon_oxides_kg"],
            }
            rows.append(row)

            case_dir = run_dir / case_name / f"x{mult:.2f}"
            case_dir.mkdir(parents=True, exist_ok=True)
            write_dataframe(ts_rows, case_dir / "timeseries.csv")
            write_summary(summary, case_dir / "summary.json")
            if make_plots:
                plot_simulation(ts_rows, case_dir)

    write_dataframe(rows, run_dir / "sensitivity_summary.csv")
    write_summary({"rows": rows}, run_dir / "sensitivity_summary.json")
    return run_dir, rows

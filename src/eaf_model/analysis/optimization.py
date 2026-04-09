from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from eaf_model.config import EAFConfig
from eaf_model.io.results import make_run_dir, write_dataframe, write_summary
from eaf_model.plotting.plots import plot_simulation
from eaf_model.simulation.core import run_simulation


def option_configs(base: EAFConfig) -> dict[str, EAFConfig]:
    return {
        "option1": replace(base, total_time_s=180.0, c_inj_kg_s=1.3, arc_power_kw=30000.0, slag_add_kg_s=3.0),
        "option2": replace(base, total_time_s=180.0, c_inj_kg_s=1.15, fm_inj_kg_s=1.4, o2_lance_kg_s=3.4, arc_power_kw=30000.0),
        "option3": replace(base, total_time_s=160.0, c_inj_kg_s=1.05, fm_inj_kg_s=1.3, o2_lance_kg_s=3.1, slag_add_kg_s=2.0),
        "option4": replace(base, total_time_s=120.0, c_inj_kg_s=0.95, fm_inj_kg_s=1.25, o2_lance_kg_s=2.8, o2_post_kg_s=0.8, slag_add_kg_s=1.5, arc_power_kw=30000.0),
    }


def run_optimization(base_cfg: EAFConfig, output_root: Path, make_plots: bool = True) -> tuple[Path, list[dict[str, float | str]]]:
    run_dir = make_run_dir(output_root, "optimization")
    rows: list[dict[str, float | str]] = []
    for name, cfg in option_configs(base_cfg).items():
        ts_rows, summary = run_simulation(cfg)
        opex_proxy = cfg.c_inj_kg_s + cfg.fm_inj_kg_s + cfg.o2_lance_kg_s + cfg.o2_post_kg_s + cfg.slag_add_kg_s
        score = (
            0.35 * summary["final"]["manganese_wt_pct"]
            - 0.25 * abs(summary["final"]["carbon_wt_pct"] - 0.5)
            - 0.20 * opex_proxy
            - 0.20 * summary["final"]["co2_to_co_ratio"]
        )
        rows.append({
            "option": name,
            "score": score,
            "opex_proxy": opex_proxy,
            "liquid_temp_k": summary["final"]["t_liquid_metal_k"],
            "carbon_wt_pct": summary["final"]["carbon_wt_pct"],
            "manganese_wt_pct": summary["final"]["manganese_wt_pct"],
            "co2_to_co_ratio": summary["final"]["co2_to_co_ratio"],
        })
        opt_dir = run_dir / name
        opt_dir.mkdir(parents=True, exist_ok=True)
        write_dataframe(ts_rows, opt_dir / "timeseries.csv")
        write_summary(summary, opt_dir / "summary.json")
        if make_plots:
            plot_simulation(ts_rows, opt_dir)

    ranking = sorted(rows, key=lambda x: float(x["score"]), reverse=True)
    write_dataframe(ranking, run_dir / "ranking.csv")
    write_summary({"ranking": ranking}, run_dir / "ranking.json")
    return run_dir, ranking

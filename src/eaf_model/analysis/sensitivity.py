from __future__ import annotations

import base64
import copy
import io
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from eaf_model.config import EAFConfig
from eaf_model.io.results import make_run_dir, write_dataframe, write_summary
from eaf_model.plotting.plots import plot_simulation
from eaf_model.simulation.core import run_simulation

PCT_VALUES = [-20, -10, -5, 0, 5, 10, 15, 20]

PCT_VALUES_BY_LABEL = {
    "Cinj": [-20, -10, 0, 10, 20],
    "Mninj": [-20, -10, 0, 10, 20],
    "O2lance": [-20, -15, -10, -5, 0, 5, 10, 15, 20],
    "O2post": [-20, -10, 0, 10, 20],
    "SlagAdd": [-20, -10, 0, 10, 20],
    "Removal Interval": [-20, -10, 0, 10, 20],
    "Parc": [-20, -10, 0, 10, 20],
    "Upper Size": [-20, -10, 0, 10, 20],
    "Lower Size": [-20, -10, 0, 10, 20],
}

STYLE = {
    "Cinj": dict(color="#0072BD", marker="o", markersize=10, markerfacecolor="none", markeredgewidth=1.5),
    "Mninj": dict(color="#D95319", marker="+", markersize=11, markeredgewidth=1.5),
    "O2lance": dict(color="#E5A30A", marker=(8, 2, 0), markersize=12, markeredgewidth=1.2),
    "O2post": dict(color="#7E2F8E", marker="o", markersize=7),
    "SlagAdd": dict(color="#66A61E", marker="x", markersize=10, markeredgewidth=1.5),
    "Removal Interval": dict(color="#4DB3E6", marker="s", markersize=8, markerfacecolor="none", markeredgewidth=1.5),
    "Parc": dict(color="#A2142F", marker="d", markersize=10, markerfacecolor="none", markeredgewidth=1.5),
    "Upper Size": dict(color="#0072BD", marker="^", markersize=10, markerfacecolor="none", markeredgewidth=1.5),
    "Lower Size": dict(color="#D95319", marker="|", markersize=14, markeredgewidth=1.5),
}


def _adjust_percent(value: float, pct: float) -> float:
    return value * (1.0 + pct / 100.0)


def _modify_case(base_cfg: EAFConfig, label: str, pct: float) -> EAFConfig:
    cfg = copy.deepcopy(base_cfg)
    if label == "Cinj":
        return replace(cfg, c_inj_kg_s=_adjust_percent(cfg.c_inj_kg_s, pct))
    if label == "Mninj":
        return replace(cfg, fm_inj_kg_s=_adjust_percent(cfg.fm_inj_kg_s, pct))
    if label == "O2lance":
        return replace(cfg, o2_lance_kg_s=_adjust_percent(cfg.o2_lance_kg_s, pct))
    if label == "O2post":
        return replace(cfg, o2_post_kg_s=_adjust_percent(cfg.o2_post_kg_s, pct))
    if label == "SlagAdd":
        return replace(cfg, slag_add_kg_s=_adjust_percent(cfg.slag_add_kg_s, pct))
    if label == "Removal Interval":
        return replace(cfg, takeout_interval_s=max(1.0, _adjust_percent(cfg.takeout_interval_s, pct)))
    if label == "Parc":
        return replace(cfg, arc_power_kw=_adjust_percent(cfg.arc_power_kw, pct))
    if label == "Upper Size":
        cfg.geometry.r_eafout_m = _adjust_percent(cfg.geometry.r_eafout_m, pct)
        return cfg
    if label == "Lower Size":
        cfg.geometry.r_eafin_m = _adjust_percent(cfg.geometry.r_eafin_m, pct)
        return cfg
    raise ValueError(label)


def _render_sensitivity_html(run_dir: Path, curves: dict[str, dict[str, list[float]]]) -> Path:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        html = run_dir / "sensitivity.html"
        html.write_text("<html><body><h1>Sensitivity Report</h1><p>matplotlib not available.</p></body></html>", encoding="utf-8")
        return html

    def chart(metric_key: str, ylabel: str, ylim: tuple[float, float] | None = None) -> str:
        fig, ax = plt.subplots(figsize=(8.5, 5.8), facecolor="white")
        ax.set_facecolor("white")
        for series_name, values in curves[metric_key].items():
            style = STYLE[series_name]
            ax.plot(PCT_VALUES_BY_LABEL[series_name], values, linewidth=1.8, label=series_name, **style)

        ax.set_xlim(-20, 20)
        if ylim:
            ax.set_ylim(*ylim)
        ax.set_xlabel("Percentage Change")
        ax.set_ylabel(ylabel)
        ax.set_xticks([-20, -15, -10, -5, 0, 5, 10, 15, 20], ["-20%", "-15%", "-10%", "-5%", "0%", "5%", "10%", "15%", "20%"])
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=5, frameon=True, fancybox=False)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    imgs = {
        "carbon": chart("carbon_wt_pct", "End Carbon %"),
        "emission": chart("offgas_carbon_oxides_kg", "Carbon Oxides Emission / kgs$^{-1}$"),
        "manganese": chart("manganese_wt_pct", "End Manganese %"),
        "ratio": chart("co2_to_co_ratio", "CO$_2$:CO Ratio"),
        "selectivity": chart("selectivity_fe", "Selectivity of Iron"),
        "temperature": chart("t_liquid_metal_k", "Liquid Metal Temperature / K"),
    }

    sections = "\n".join(
        f"<h2>{title}</h2><img src='data:image/png;base64,{img}' style='max-width:100%;'/>"
        for title, img in [
            ("End Carbon Sensitivity", imgs["carbon"]),
            ("Carbon Oxides Emission Sensitivity", imgs["emission"]),
            ("End Manganese Sensitivity", imgs["manganese"]),
            ("CO2:CO Ratio Sensitivity", imgs["ratio"]),
            ("Selectivity of Iron Sensitivity", imgs["selectivity"]),
            ("Liquid Metal Temperature Sensitivity", imgs["temperature"]),
        ]
    )

    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Sensitivity Report</title>
<style>body{{font-family:Arial,sans-serif;background:white;margin:20px;}} section{{background:#fff;padding:14px;margin-bottom:14px;border:1px solid #ddd;}}</style>
</head><body>
<h1>EAF Sensitivity Analysis Report</h1>
<p>All curves in this report are generated directly from the migrated Python sensitivity analysis runs.</p>
<section>{sections}</section>
<section><h2>Generated sensitivity payload</h2><pre>{json.dumps(curves, indent=2)}</pre></section>
</body></html>"""

    out = run_dir / "sensitivity.html"
    out.write_text(html, encoding="utf-8")
    return out


def run_sensitivity(base_cfg: EAFConfig, output_root: Path, make_plots: bool = True) -> tuple[Path, list[dict[str, float | str]]]:
    run_dir = make_run_dir(output_root, "sensitivity")
    labels = ["Cinj", "Mninj", "O2lance", "O2post", "SlagAdd", "Removal Interval", "Parc", "Upper Size", "Lower Size"]
    rows: list[dict[str, float | str]] = []

    curves: dict[str, dict[str, list[float]]] = {
        "carbon_wt_pct": {k: [] for k in labels},
        "offgas_carbon_oxides_kg": {k: [] for k in labels},
        "manganese_wt_pct": {k: [] for k in labels},
        "co2_to_co_ratio": {k: [] for k in labels},
        "selectivity_fe": {k: [] for k in labels},
        "t_liquid_metal_k": {k: [] for k in labels},
    }

    default_cfg = EAFConfig()
    cfg_for_sensitivity = base_cfg
    if base_cfg.total_time_s == default_cfg.total_time_s and base_cfg.takeout_interval_s == default_cfg.takeout_interval_s:
        cfg_for_sensitivity = replace(base_cfg, takeout_interval_s=600.0)

    for label in labels:
        for pct in PCT_VALUES_BY_LABEL[label]:
            cfg = _modify_case(cfg_for_sensitivity, label, pct)
            ts_rows, summary = run_simulation(cfg)

            selectivity = 1000.0 + 2.2 * summary["final"]["t_liquid_metal_k"] - 8.0 * summary["final"]["co2_to_co_ratio"]
            metrics = {
                "carbon_wt_pct": float(summary["final"]["carbon_wt_pct"]),
                "offgas_carbon_oxides_kg": float(summary["final"]["offgas_carbon_oxides_kg"]),
                "manganese_wt_pct": float(summary["final"]["manganese_wt_pct"]),
                "co2_to_co_ratio": float(summary["final"]["co2_to_co_ratio"]),
                "selectivity_fe": selectivity,
                "t_liquid_metal_k": float(summary["final"]["t_liquid_metal_k"]),
            }

            for k, v in metrics.items():
                curves[k][label].append(v)

            rows.append({"parameter": label, "pct_change": pct, **metrics})

            case_dir = run_dir / label.replace(" ", "_") / f"{pct:+d}pct"
            case_dir.mkdir(parents=True, exist_ok=True)
            write_dataframe(ts_rows, case_dir / "timeseries.csv")
            write_summary(summary, case_dir / "summary.json")
            if make_plots:
                plot_simulation(ts_rows, case_dir)

    write_dataframe(rows, run_dir / "sensitivity_summary.csv")
    write_summary({"rows": rows, "curves": curves}, run_dir / "sensitivity_summary.json")
    _render_sensitivity_html(run_dir, curves)
    return run_dir, rows

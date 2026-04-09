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

# Approximate legacy MATLAB sensitivity traces (digitized from old figures for comparison).
LEGACY_CURVES = {
    "carbon_wt_pct": {
        "Cinj": [0.498, 0.510, 0.515, 0.523, 0.530, 0.538, 0.545, 0.552],
        "Mninj": [0.519, 0.521, 0.522, 0.523, 0.524, 0.526, 0.528, 0.530],
        "O2lance": [0.66, 0.63, 0.57, 0.523, 0.477, 0.445, 0.430, 0.420],
        "O2post": [0.493, 0.505, 0.512, 0.523, 0.540, 0.556, 0.556, 0.556],
        "SlagAdd": [0.498, 0.509, 0.515, 0.523, 0.530, 0.539, 0.548, 0.556],
        "Removal Interval": [0.510, 0.517, 0.520, 0.523, 0.526, 0.529, 0.531, 0.533],
        "Parc": [0.523, 0.523, 0.523, 0.523, 0.523, 0.523, 0.523, 0.523],
        "Upper Size": [0.525, 0.524, 0.5235, 0.523, 0.5227, 0.5225, 0.5223, 0.5221],
        "Lower Size": [0.522, 0.5224, 0.5227, 0.523, 0.5233, 0.5236, 0.5238, 0.524],
    },
    "offgas_carbon_oxides_kg": {
        "Cinj": [6.065, 6.10, 6.115, 6.125, 6.14, 6.155, 6.17, 6.185],
        "Mninj": [6.10, 6.115, 6.122, 6.125, 6.132, 6.138, 6.145, 6.152],
        "O2lance": [5.55, 5.72, 5.90, 6.125, 6.35, 6.58, 6.76, 6.95],
        "O2post": [6.01, 6.075, 6.10, 6.125, 6.12, 6.115, 6.10, 6.05],
        "SlagAdd": [6.165, 6.145, 6.135, 6.125, 6.115, 6.105, 6.095, 6.08],
        "Removal Interval": [6.085, 6.10, 6.115, 6.125, 6.118, 6.115, 6.120, 6.125],
        "Parc": [6.14, 6.135, 6.130, 6.125, 6.123, 6.120, 6.117, 6.115],
        "Upper Size": [6.09, 6.12, 6.125, 6.125, 6.125, 6.125, 6.126, 6.127],
        "Lower Size": [6.095, 6.110, 6.120, 6.125, 6.130, 6.135, 6.145, 6.155],
    },
    "manganese_wt_pct": {
        "Cinj": [0.66, 0.68, 0.69, 0.70, 0.71, 0.722, 0.732, 0.742],
        "Mninj": [0.565, 0.632, 0.668, 0.70, 0.737, 0.773, 0.810, 0.847],
        "O2lance": [0.772, 0.735, 0.724, 0.70, 0.674, 0.640, 0.610, 0.585],
        "O2post": [0.762, 0.738, 0.720, 0.70, 0.673, 0.635, 0.610, 0.588],
        "SlagAdd": [0.706, 0.704, 0.702, 0.70, 0.698, 0.697, 0.694, 0.691],
        "Removal Interval": [0.720, 0.710, 0.705, 0.70, 0.697, 0.693, 0.690, 0.687],
        "Parc": [0.702, 0.701, 0.7005, 0.70, 0.6998, 0.6996, 0.6994, 0.6992],
        "Upper Size": [0.699, 0.700, 0.7004, 0.70, 0.7002, 0.7004, 0.7005, 0.7006],
        "Lower Size": [0.701, 0.701, 0.7008, 0.70, 0.7002, 0.7004, 0.7006, 0.7008],
    },
    "co2_to_co_ratio": {
        "Cinj": [11.1, 10.4, 10.1, 9.8, 9.5, 9.3, 9.1, 8.9],
        "Mninj": [10.4, 10.1, 9.95, 9.8, 9.65, 9.55, 9.45, 9.35],
        "O2lance": [15.8, 12.9, 10.9, 9.8, 9.1, 8.6, 8.25, 7.85],
        "O2post": [5.5, 7.1, 8.5, 9.8, 12.2, 15.5, 20.0, 26.0],
        "SlagAdd": [8.7, 9.2, 9.5, 9.8, 10.1, 10.5, 10.9, 11.4],
        "Removal Interval": [8.7, 9.3, 9.55, 9.8, 9.9, 10.05, 10.2, 10.4],
        "Parc": [9.8, 9.79, 9.79, 9.8, 9.79, 9.79, 9.79, 9.79],
        "Upper Size": [10.0, 9.96, 9.90, 9.8, 9.76, 9.75, 9.74, 9.73],
        "Lower Size": [9.9, 9.88, 9.84, 9.8, 9.78, 9.77, 9.77, 9.76],
    },
    "selectivity_fe": {
        "Cinj": [1520, 1665, 1745, 1820, 1900, 1980, 2060, 2150],
        "Mninj": [1890, 1850, 1835, 1820, 1810, 1800, 1790, 1780],
        "O2lance": [2620, 2390, 2140, 1820, 1510, 1240, 1010, 790],
        "O2post": [2025, 1935, 1880, 1820, 1730, 1640, 1540, 1445],
        "SlagAdd": [1870, 1845, 1830, 1820, 1810, 1795, 1780, 1765],
        "Removal Interval": [1840, 1835, 1828, 1820, 1815, 1805, 1798, 1792],
        "Parc": [1820, 1819, 1819, 1820, 1820, 1821, 1821, 1822],
        "Upper Size": [1790, 1812, 1820, 1820, 1818, 1815, 1813, 1812],
        "Lower Size": [1810, 1814, 1817, 1820, 1823, 1826, 1829, 1832],
    },
    "t_liquid_metal_k": {
        "Cinj": [2056, 2052, 2050, 2048, 2045, 2042, 2040, 2038],
        "Mninj": [2185, 2108, 2075, 2048, 2022, 1998, 1976, 1955],
        "O2lance": [1953, 1999, 2023, 2048, 2072, 2094, 2112, 2122],
        "O2post": [2011, 2029, 2040, 2048, 2058, 2068, 2074, 2080],
        "SlagAdd": [2048, 2048, 2047, 2048, 2047, 2046, 2046, 2045],
        "Removal Interval": [2070, 2056, 2052, 2048, 2044, 2040, 2037, 2034],
        "Parc": [2010, 2029, 2040, 2048, 2058, 2066, 2076, 2085],
        "Upper Size": [2280, 2104, 2070, 2048, 2024, 2002, 1982, 1957],
        "Lower Size": [2185, 2108, 2074, 2048, 2022, 1998, 1976, 1955],
    },
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


def _render_sensitivity_html(run_dir: Path, old_curves: dict[str, dict[str, list[float]]], new_curves: dict[str, dict[str, list[float]]]) -> Path:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        html = run_dir / "sensitivity.html"
        html.write_text("<html><body><h1>Sensitivity Report</h1><p>matplotlib not available.</p></body></html>", encoding="utf-8")
        return html

    def chart(metric_key: str, ylabel: str, ylim: tuple[float, float] | None = None) -> str:
        fig, ax = plt.subplots(figsize=(8.5, 5.8), facecolor="#E5E5E5")
        ax.set_facecolor("#E5E5E5")
        for series_name, values in old_curves[metric_key].items():
            style = STYLE[series_name]
            ax.plot(PCT_VALUES, values, linewidth=1.4, label=series_name, **style)
            # overlay migrated model points (dashed)
            nv = new_curves[metric_key][series_name]
            ax.plot(PCT_VALUES, nv, linestyle="--", color=style["color"], linewidth=0.9, alpha=0.5)

        ax.set_xlim(-20, 20)
        if ylim:
            ax.set_ylim(*ylim)
        ax.set_xlabel("Percentage Change")
        ax.set_ylabel(ylabel)
        ax.set_xticks([-20, -15, -10, -5, 0, 5, 10, 15, 20], ["-20%", "-15%", "-10%", "-5%", "0%", "5%", "10%", "15%", "20%"])
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=5, frameon=True, fancybox=False)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="#E5E5E5")
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    imgs = {
        "carbon": chart("carbon_wt_pct", "End Carbon %", (0.45, 0.60)),
        "emission": chart("offgas_carbon_oxides_kg", "Carbon Oxides Emission / kgs$^{-1}$", (5.8, 6.4)),
        "manganese": chart("manganese_wt_pct", "End Manganese %", (0.55, 0.85)),
        "ratio": chart("co2_to_co_ratio", "CO$_2$:CO Ratio", (5.0, 15.0)),
        "selectivity": chart("selectivity_fe", "Selectivity of Iron", (1250, 2250)),
        "temperature": chart("t_liquid_metal_k", "Liquid Metal Temperature / K", (1950, 2200)),
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
<style>body{{font-family:Arial,sans-serif;background:#f7f7f7;margin:20px;}} section{{background:#fff;padding:14px;margin-bottom:14px;border:1px solid #ddd;}} code{{background:#eee;padding:1px 4px;}}</style>
</head><body>
<h1>EAF Sensitivity Comparison Report</h1>
<p>Solid lines = legacy MATLAB reference trends (from historical sensitivity figures). Dashed lines = migrated Python model outputs at identical percentage changes.</p>
<section>{sections}</section>
<section><h2>Reference payload</h2><pre>{json.dumps(old_curves, indent=2)}</pre></section>
</body></html>"""

    out = run_dir / "sensitivity.html"
    out.write_text(html, encoding="utf-8")
    return out


def run_sensitivity(base_cfg: EAFConfig, output_root: Path, make_plots: bool = True) -> tuple[Path, list[dict[str, float | str]]]:
    run_dir = make_run_dir(output_root, "sensitivity")
    labels = ["Cinj", "Mninj", "O2lance", "O2post", "SlagAdd", "Removal Interval", "Parc", "Upper Size", "Lower Size"]
    rows: list[dict[str, float | str]] = []

    new_curves: dict[str, dict[str, list[float]]] = {
        "carbon_wt_pct": {k: [] for k in labels},
        "offgas_carbon_oxides_kg": {k: [] for k in labels},
        "manganese_wt_pct": {k: [] for k in labels},
        "co2_to_co_ratio": {k: [] for k in labels},
        "selectivity_fe": {k: [] for k in labels},
        "t_liquid_metal_k": {k: [] for k in labels},
    }

    for label in labels:
        for pct in PCT_VALUES:
            cfg = _modify_case(base_cfg, label, pct)
            ts_rows, summary = run_simulation(cfg)

            # proxy selectivity retained from migration simplification
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
                new_curves[k][label].append(v)

            rows.append({"parameter": label, "pct_change": pct, **metrics})

            case_dir = run_dir / label.replace(" ", "_") / f"{pct:+d}pct"
            case_dir.mkdir(parents=True, exist_ok=True)
            write_dataframe(ts_rows, case_dir / "timeseries.csv")
            write_summary(summary, case_dir / "summary.json")
            if make_plots:
                plot_simulation(ts_rows, case_dir)

    write_dataframe(rows, run_dir / "sensitivity_summary.csv")
    write_summary({"rows": rows, "legacy_reference": LEGACY_CURVES}, run_dir / "sensitivity_summary.json")
    _render_sensitivity_html(run_dir, LEGACY_CURVES, new_curves)
    return run_dir, rows

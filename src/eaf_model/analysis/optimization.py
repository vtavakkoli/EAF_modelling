from __future__ import annotations

import base64
import io
import json
from dataclasses import replace
from pathlib import Path
from statistics import mean
from typing import Any

from eaf_model.config import EAFConfig
from eaf_model.io.results import make_run_dir, write_dataframe, write_summary
from eaf_model.plotting.plots import plot_simulation
from eaf_model.simulation.core import run_simulation

BLUE = "#0072BD"
ORANGE = "#D95319"
GREEN_BG = "#A9D18E"
RED_BG = "#E6B8C0"


def option_configs(base: EAFConfig) -> dict[str, EAFConfig]:
    option2_secs = base.total_time_s
    option1_secs = base.total_time_s * 1.5
    option3_secs = base.total_time_s * 3.0
    option4_secs = base.total_time_s

    return {
        "option1": replace(base, total_time_s=option1_secs, c_inj_kg_s=1.30, fm_inj_kg_s=1.50, o2_lance_kg_s=4.00, o2_post_kg_s=1.00, slag_add_kg_s=3.00, takeout_interval_s=600.0, arc_power_kw=30000.0),
        "option2": replace(base, total_time_s=option2_secs, c_inj_kg_s=0.95, fm_inj_kg_s=1.25, o2_lance_kg_s=2.80, o2_post_kg_s=0.80, slag_add_kg_s=1.50, takeout_interval_s=600.0, arc_power_kw=30000.0),
        "option3": replace(
            base,
            total_time_s=option3_secs,
            c_inj_kg_s=0.95,
            fm_inj_kg_s=1.25,
            o2_lance_kg_s=2.80,
            o2_post_kg_s=0.80,
            slag_add_kg_s=1.50,
            takeout_interval_s=900.0,
            arc_power_kw=30000.0,
            geometry=replace(base.geometry, r_eafout_m=3.72, r_eafin_m=3.62),
        ),
        "option4": replace(
            base,
            total_time_s=option4_secs,
            c_inj_kg_s=0.95,
            fm_inj_kg_s=1.25,
            o2_lance_kg_s=2.80,
            o2_post_kg_s=0.80,
            slag_add_kg_s=1.50,
            takeout_interval_s=600.0,
            arc_power_kw=30000.0,
            geometry=replace(base.geometry, r_eafout_m=3.485, r_eafin_m=3.385),
        ),
    }


def _as_float(value: Any) -> float:
    return float(value)


def _plot_to_base64(plotter: Any) -> str:
    buffer = io.BytesIO()
    plotter.savefig(buffer, format="png", dpi=140, bbox_inches="tight", facecolor="#E5E5E5")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("ascii")


def _build_comparison_from_runs(option_data: dict[str, dict[str, Any]], ranking: list[dict[str, float | str]]) -> dict[str, Any]:
    initial_name = "option1"
    optimized_name = str(ranking[0]["option"])

    init = option_data[initial_name]
    opt = option_data[optimized_name]
    init_rows = init["timeseries"]
    opt_rows = opt["timeseries"]
    init_cfg: EAFConfig = init["config"]
    opt_cfg: EAFConfig = opt["config"]

    def minmax(rows: list[dict[str, float]], key: str) -> tuple[float, float]:
        vals = [float(r[key]) for r in rows]
        return min(vals), max(vals)

    i_c_min, i_c_max = minmax(init_rows, "carbon_wt_pct")
    o_c_min, o_c_max = minmax(opt_rows, "carbon_wt_pct")
    i_mn_min, i_mn_max = minmax(init_rows, "manganese_wt_pct")
    o_mn_min, o_mn_max = minmax(opt_rows, "manganese_wt_pct")

    def selectivity(final: dict[str, float]) -> float:
        return 1000.0 + 2.2 * float(final["t_liquid_metal_k"]) - 8.0 * float(final["co2_to_co_ratio"])

    return {
        "source": {"initial_option": initial_name, "optimized_option": optimized_name},
        "carbon_wt_pct": {
            "initial": float(init["summary"]["final"]["carbon_wt_pct"]),
            "optimized": float(opt["summary"]["final"]["carbon_wt_pct"]),
            "initial_min": i_c_min,
            "initial_max": i_c_max,
            "optimized_min": o_c_min,
            "optimized_max": o_c_max,
        },
        "manganese_wt_pct": {
            "initial": float(init["summary"]["final"]["manganese_wt_pct"]),
            "optimized": float(opt["summary"]["final"]["manganese_wt_pct"]),
            "initial_min": i_mn_min,
            "initial_max": i_mn_max,
            "optimized_min": o_mn_min,
            "optimized_max": o_mn_max,
        },
        "avg_acc_solid_metal_kg": {
            "initial": mean(float(r["m_solid_kg"]) for r in init_rows),
            "optimized": mean(float(r["m_solid_kg"]) for r in opt_rows),
        },
        "outlet_liquid_temp_k": {
            "initial": float(init["summary"]["final"]["t_liquid_metal_k"]),
            "optimized": float(opt["summary"]["final"]["t_liquid_metal_k"]),
        },
        "selectivity_fe": {
            "initial": selectivity(init["summary"]["final"]),
            "optimized": selectivity(opt["summary"]["final"]),
        },
        "material_rates": {
            "initial": {"Cinj": init_cfg.c_inj_kg_s, "Mninj": init_cfg.fm_inj_kg_s, "O2,lance": init_cfg.o2_lance_kg_s, "O2,post": init_cfg.o2_post_kg_s, "Slag": init_cfg.slag_add_kg_s},
            "optimized": {"Cinj": opt_cfg.c_inj_kg_s, "Mninj": opt_cfg.fm_inj_kg_s, "O2,lance": opt_cfg.o2_lance_kg_s, "O2,post": opt_cfg.o2_post_kg_s, "Slag": opt_cfg.slag_add_kg_s},
        },
        "carbon_oxides_emission": {
            "initial": float(init["summary"]["final"]["offgas_carbon_oxides_kg"]),
            "optimized": float(opt["summary"]["final"]["offgas_carbon_oxides_kg"]),
        },
        "co2_to_co_ratio": {
            "initial": float(init["summary"]["final"]["co2_to_co_ratio"]),
            "optimized": float(opt["summary"]["final"]["co2_to_co_ratio"]),
        },
    }


def _composition_panel(ax: Any, data: dict[str, float], ylabel: str, y_limits: tuple[float, float], green_range: tuple[float, float]) -> None:
    from matplotlib.lines import Line2D

    ax.set_facecolor("#E5E5E5")
    ax.axhspan(y_limits[0], green_range[0], color=RED_BG, alpha=0.9)
    ax.axhspan(green_range[0], green_range[1], color=GREEN_BG, alpha=0.9)
    ax.axhspan(green_range[1], y_limits[1], color=RED_BG, alpha=0.9)

    x_initial, x_opt = 0.0, 1.0
    ax.plot([x_initial, x_initial], [data["initial_min"], data["initial_max"]], color=BLUE, linewidth=1.5)
    ax.plot([x_opt, x_opt], [data["optimized_min"], data["optimized_max"]], color=ORANGE, linewidth=1.5)
    ax.scatter([x_initial], [data["initial"]], s=230, facecolors="none", edgecolors=BLUE, linewidths=1.5, marker="o", zorder=3)
    ax.scatter([x_opt], [data["optimized"]], s=230, facecolors="none", edgecolors=ORANGE, linewidths=1.5, marker="o", zorder=3)
    ax.scatter([x_initial, x_initial], [data["initial_min"], data["initial_max"]], s=45, facecolors="none", edgecolors=BLUE, linewidths=1.5, marker="v", zorder=3)
    ax.scatter([x_opt, x_opt], [data["optimized_min"], data["optimized_max"]], s=45, facecolors="none", edgecolors=ORANGE, linewidths=1.5, marker="v", zorder=3)

    data_min = min(data["initial_min"], data["optimized_min"], y_limits[0])
    data_max = max(data["initial_max"], data["optimized_max"], y_limits[1])
    span = max(data_max - data_min, 1e-9)
    y_min = data_min - 0.05 * span
    y_max = data_max + 0.05 * span

    ax.set_xlim(-0.7, 1.7)
    ax.set_xticks([])
    ax.set_ylim(y_min, y_max)
    ax.set_ylabel(ylabel)

    handles = [
        Line2D([0], [0], color=BLUE, marker="o", markersize=10, markerfacecolor="none", label="Initial"),
        Line2D([0], [0], color=ORANGE, marker="o", markersize=10, markerfacecolor="none", label="Optimised"),
    ]
    ax.legend(handles=handles, loc="lower center", ncol=2, frameon=True, framealpha=1.0, fancybox=False)


def _build_report_charts(model_comparison: dict[str, dict[str, float]]) -> dict[str, str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return {}

    charts: dict[str, str] = {}

    fig, axes = plt.subplots(1, 2, figsize=(10, 5), facecolor="#E5E5E5")
    _composition_panel(axes[0], model_comparison["carbon_wt_pct"], "Carbon Composition / %", (0.40, 0.60), (0.48, 0.55))
    _composition_panel(axes[1], model_comparison["manganese_wt_pct"], "Manganese Composition / %", (0.45, 1.00), (0.60, 0.90))
    charts["composition"] = _plot_to_base64(fig)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(11, 4), facecolor="#E5E5E5")
    for ax, key, title in [
        (axes[0], "avg_acc_solid_metal_kg", "Average Accumulated Solid Metal / kg"),
        (axes[1], "outlet_liquid_temp_k", "Outlet Liquid Temperature / K"),
        (axes[2], "selectivity_fe", "Selectivity"),
    ]:
        data = model_comparison[key]
        ax.set_facecolor("#E5E5E5")
        ax.bar([0], [data["initial"]], color=BLUE, width=0.35, label="Initial")
        ax.bar([0.45], [data["optimized"]], color=ORANGE, width=0.35, label="Optimised")
        ax.set_xticks([])
        ax.set_title(title)
    axes[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
    charts["efficiency"] = _plot_to_base64(fig)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4), facecolor="#E5E5E5")
    ax.set_facecolor("#E5E5E5")
    rates_i = model_comparison["material_rates"]["initial"]
    rates_o = model_comparison["material_rates"]["optimized"]
    labels = list(rates_i.keys())
    x = list(range(len(labels)))
    width = 0.28
    ax.bar([i - width / 2 for i in x], [rates_i[l] for l in labels], width=width, label="Initial", color=BLUE)
    ax.bar([i + width / 2 for i in x], [rates_o[l] for l in labels], width=width, label="Optimised", color=ORANGE)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Material Addition Rate / kg s$^{-1}$")
    ax.legend(loc="upper right")
    charts["material"] = _plot_to_base64(fig)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8, 4), facecolor="#E5E5E5")
    for ax, key, title in [
        (axes[0], "carbon_oxides_emission", "Emission of Carbon Oxides / kg s$^{-1}$"),
        (axes[1], "co2_to_co_ratio", "CO$_2$ : CO Ratio"),
    ]:
        data = model_comparison[key]
        ax.set_facecolor("#E5E5E5")
        ax.bar([0], [data["initial"]], color=BLUE, width=0.35, label="Initial")
        ax.bar([0.45], [data["optimized"]], color=ORANGE, width=0.35, label="Optimised")
        ax.set_xticks([])
        ax.set_title(title)
    axes[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    charts["safety"] = _plot_to_base64(fig)
    plt.close(fig)

    return charts


def _build_optimization_html(
    ranking: list[dict[str, float | str]],
    option_rows: list[dict[str, float | str]],
    model_comparison: dict[str, Any],
    run_dir: Path,
) -> Path:
    charts = _build_report_charts(model_comparison)

    option_table_rows = "\n".join(
        f"<tr><td>{r['option']}</td><td>{r['c_inj_kg_s']:.2f}</td><td>{r['fm_inj_kg_s']:.2f}</td><td>{r['o2_lance_kg_s']:.2f}</td><td>{r['o2_post_kg_s']:.2f}</td><td>{r['slag_add_kg_s']:.2f}</td><td>{r['takeout_interval_s']:.0f}</td><td>{r['arc_power_kw']:.0f}</td><td>{r['capacity_tonnes']:.0f}</td></tr>"
        for r in option_rows
    )
    ranking_rows = "\n".join(
        f"<tr><td>{r['option']}</td><td>{_as_float(r['score']):.4f}</td><td>{_as_float(r['carbon_wt_pct']):.4f}</td><td>{_as_float(r['manganese_wt_pct']):.4f}</td><td>{_as_float(r['co2_to_co_ratio']):.4f}</td></tr>"
        for r in ranking
    )

    def img_block(name: str, title: str) -> str:
        if name not in charts:
            return f"<h3>{title}</h3><p>Chart unavailable (matplotlib not installed in runtime).</p>"
        return f"<h3>{title}</h3><img src='data:image/png;base64,{charts[name]}' alt='{title}' style='max-width:100%;'/>"

    html = f"""<!doctype html>
<html><head><meta charset='utf-8'/><title>EAF Optimization Report</title>
<style>
body{{font-family:Arial,sans-serif;margin:24px;background:#fafafa;}}
section{{background:#fff;padding:18px;margin-bottom:16px;border:1px solid #ddd;}}
table{{border-collapse:collapse;width:100%;margin-top:8px;}}
th,td{{border:1px solid #999;padding:8px;text-align:center;}}
th{{background:#f0f0f0;}}
</style></head><body>
<h1>EAF Optimization Report</h1>
<p>This report is generated entirely from current optimization run data.</p>
<p>Initial option: <strong>{model_comparison['source']['initial_option']}</strong>; Optimized option: <strong>{model_comparison['source']['optimized_option']}</strong>.</p>

<section>
<h2>KPI categories</h2>
<table>
<tr><th>KPI Category</th><th>KPIs Considered</th></tr>
<tr><td>Composition Requirements</td><td>Carbon Composition, Manganese Composition</td></tr>
<tr><td>Economics</td><td>CAPEX, OPEX</td></tr>
<tr><td>Safety & Environment</td><td>Carbon Oxide Emissions, CO<sub>2</sub>:CO Ratio</td></tr>
<tr><td>Operational Efficiency</td><td>Liquid Metal Outlet Temperature, Selectivity of Fe</td></tr>
</table>
</section>

<section>
<h2>Optimization options</h2>
<table>
<tr><th>Option</th><th>Cinj (kg/s)</th><th>Mninj (kg/s)</th><th>O2,lance (kg/s)</th><th>O2,post (kg/s)</th><th>Slag (kg/s)</th><th>Removal Interval (s)</th><th>Arc Power (kW)</th><th>Capacity (tonnes)</th></tr>
{option_table_rows}
</table>
</section>

<section>
<h2>Ranked options from migrated Python model</h2>
<table>
<tr><th>Option</th><th>Score</th><th>Carbon wt%</th><th>Manganese wt%</th><th>CO<sub>2</sub>:CO</th></tr>
{ranking_rows}
</table>
</section>

<section>{img_block('composition','Composition comparison')}</section>
<section>{img_block('efficiency','Operational efficiency comparison')}</section>
<section>{img_block('material','Material input rates comparison')}</section>
<section>{img_block('safety','Safety and environment comparison')}</section>

<section>
<h2>Generated comparison payload (JSON)</h2>
<pre>{json.dumps(model_comparison, indent=2)}</pre>
</section>

</body></html>"""

    out_path = run_dir / "optimization.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def run_optimization(base_cfg: EAFConfig, output_root: Path, make_plots: bool = True) -> tuple[Path, list[dict[str, float | str]]]:
    run_dir = make_run_dir(output_root, "optimization")
    rows: list[dict[str, float | str]] = []
    option_rows: list[dict[str, float | str]] = []
    option_data: dict[str, dict[str, Any]] = {}

    for name, cfg in option_configs(base_cfg).items():
        ts_rows, summary = run_simulation(cfg)
        option_data[name] = {"timeseries": ts_rows, "summary": summary, "config": cfg}
        opex_proxy = cfg.c_inj_kg_s + cfg.fm_inj_kg_s + cfg.o2_lance_kg_s + cfg.o2_post_kg_s + cfg.slag_add_kg_s
        score = (
            0.35 * summary["final"]["manganese_wt_pct"]
            - 0.25 * abs(summary["final"]["carbon_wt_pct"] - 0.5)
            - 0.20 * opex_proxy
            - 0.20 * summary["final"]["co2_to_co_ratio"]
        )
        rows.append(
            {
                "option": name,
                "score": score,
                "opex_proxy": opex_proxy,
                "liquid_temp_k": summary["final"]["t_liquid_metal_k"],
                "carbon_wt_pct": summary["final"]["carbon_wt_pct"],
                "manganese_wt_pct": summary["final"]["manganese_wt_pct"],
                "co2_to_co_ratio": summary["final"]["co2_to_co_ratio"],
            }
        )
        option_rows.append(
            {
                "option": name,
                "c_inj_kg_s": cfg.c_inj_kg_s,
                "fm_inj_kg_s": cfg.fm_inj_kg_s,
                "o2_lance_kg_s": cfg.o2_lance_kg_s,
                "o2_post_kg_s": cfg.o2_post_kg_s,
                "slag_add_kg_s": cfg.slag_add_kg_s,
                "takeout_interval_s": cfg.takeout_interval_s,
                "arc_power_kw": cfg.arc_power_kw,
                "capacity_tonnes": 200.0 if name in {"option1", "option2"} else (220.0 if name == "option3" else 180.0),
            }
        )

        opt_dir = run_dir / name
        opt_dir.mkdir(parents=True, exist_ok=True)
        write_dataframe(ts_rows, opt_dir / "timeseries.csv")
        write_summary(summary, opt_dir / "summary.json")
        if make_plots:
            plot_simulation(ts_rows, opt_dir)

    ranking = sorted(rows, key=lambda x: float(x["score"]), reverse=True)
    model_comparison = _build_comparison_from_runs(option_data, ranking)

    write_dataframe(ranking, run_dir / "ranking.csv")
    write_dataframe(option_rows, run_dir / "options.csv")
    write_summary({"ranking": ranking, "comparison": model_comparison}, run_dir / "ranking.json")
    _build_optimization_html(ranking=ranking, option_rows=option_rows, model_comparison=model_comparison, run_dir=run_dir)
    return run_dir, ranking

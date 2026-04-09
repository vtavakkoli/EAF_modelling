from __future__ import annotations

import base64
import io
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from eaf_model.config import EAFConfig
from eaf_model.io.results import make_run_dir, write_dataframe, write_summary
from eaf_model.plotting.plots import plot_simulation
from eaf_model.simulation.core import run_simulation


OLD_MODEL_REFERENCE = {
    "carbon_wt_pct": {"initial": 0.523, "optimized": 0.512, "initial_min": 0.505, "initial_max": 0.560, "optimized_min": 0.501, "optimized_max": 0.540},
    "manganese_wt_pct": {"initial": 0.700, "optimized": 0.680, "initial_min": 0.580, "initial_max": 0.750, "optimized_min": 0.590, "optimized_max": 0.710},
    "avg_acc_solid_metal_kg": {"initial": 1420.0, "optimized": 1360.0},
    "outlet_liquid_temp_k": {"initial": 2050.0, "optimized": 1940.0},
    "selectivity_fe": {"initial": 1800.0, "optimized": 4330.0},
    "material_rates": {
        "initial": {"C_inj": 1.3, "Mn_inj": 1.5, "O2_lance": 4.0, "O2_post": 1.0, "Slag": 3.0},
        "optimized": {"C_inj": 0.95, "Mn_inj": 1.25, "O2_lance": 2.8, "O2_post": 0.8, "Slag": 1.5},
    },
    "carbon_oxides_emission": {"initial": 6.1, "optimized": 4.6},
    "co2_to_co_ratio": {"initial": 9.8, "optimized": 10.8},
}


def option_configs(base: EAFConfig) -> dict[str, EAFConfig]:
    return {
        "option1": replace(base, total_time_s=180.0, c_inj_kg_s=1.3, arc_power_kw=30000.0, slag_add_kg_s=3.0),
        "option2": replace(base, total_time_s=180.0, c_inj_kg_s=0.95, fm_inj_kg_s=1.25, o2_lance_kg_s=2.8, o2_post_kg_s=0.8, slag_add_kg_s=1.5),
        "option3": replace(base, total_time_s=180.0, c_inj_kg_s=0.95, fm_inj_kg_s=1.25, o2_lance_kg_s=2.8, o2_post_kg_s=0.8, slag_add_kg_s=1.5, takeout_interval_s=900.0),
        "option4": replace(base, total_time_s=120.0, c_inj_kg_s=0.95, fm_inj_kg_s=1.25, o2_lance_kg_s=2.8, o2_post_kg_s=0.8, slag_add_kg_s=1.5),
    }


def _as_float(value: Any) -> float:
    return float(value)


def _plot_to_base64(plotter: Any) -> str:
    buffer = io.BytesIO()
    plotter.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("ascii")


def _build_report_charts(model_comparison: dict[str, dict[str, float]]) -> dict[str, str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return {}

    charts: dict[str, str] = {}

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, key, title in [
        (axes[0], "carbon_wt_pct", "Carbon composition / %"),
        (axes[1], "manganese_wt_pct", "Manganese composition / %"),
    ]:
        data = model_comparison[key]
        ax.errorbar([0], [data["initial"]], yerr=[[data["initial"] - data["initial_min"]], [data["initial_max"] - data["initial"]]], fmt="o", label="Initial")
        ax.errorbar([1], [data["optimized"]], yerr=[[data["optimized"] - data["optimized_min"]], [data["optimized_max"] - data["optimized"]]], fmt="o", label="Optimized")
        ax.set_xticks([0, 1], ["Initial", "Optimized"])
        ax.set_title(title)
        ax.legend()
    charts["composition"] = _plot_to_base64(fig)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    for ax, key, title in [
        (axes[0], "avg_acc_solid_metal_kg", "Avg accumulated solid metal / kg"),
        (axes[1], "outlet_liquid_temp_k", "Outlet liquid temperature / K"),
        (axes[2], "selectivity_fe", "Selectivity"),
    ]:
        data = model_comparison[key]
        ax.bar(["Initial", "Optimized"], [data["initial"], data["optimized"]])
        ax.set_title(title)
    charts["efficiency"] = _plot_to_base64(fig)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    rates_i = model_comparison["material_rates"]["initial"]
    rates_o = model_comparison["material_rates"]["optimized"]
    labels = list(rates_i.keys())
    x = list(range(len(labels)))
    width = 0.35
    ax.bar([i - width / 2 for i in x], [rates_i[l] for l in labels], width=width, label="Initial")
    ax.bar([i + width / 2 for i in x], [rates_o[l] for l in labels], width=width, label="Optimized")
    ax.set_xticks(x, labels)
    ax.set_ylabel("kg/s")
    ax.legend()
    charts["material"] = _plot_to_base64(fig)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    for ax, key, title in [
        (axes[0], "carbon_oxides_emission", "Emission of carbon oxides / kg/s"),
        (axes[1], "co2_to_co_ratio", "CO2:CO ratio"),
    ]:
        data = model_comparison[key]
        ax.bar(["Initial", "Optimized"], [data["initial"], data["optimized"]])
        ax.set_title(title)
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
code{{background:#f3f3f3;padding:2px 4px;}}
</style></head><body>
<h1>EAF Optimization Report</h1>
<p>Generated from Python optimization workflow to compare migrated model outputs against legacy MATLAB reference KPI snapshots.</p>

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
<tr><th>Option</th><th>C<sub>inj</sub> (kg/s)</th><th>Mn<sub>inj</sub> (kg/s)</th><th>O<sub>2,lance</sub> (kg/s)</th><th>O<sub>2,post</sub> (kg/s)</th><th>Slag (kg/s)</th><th>Removal Interval (s)</th><th>Arc Power (kW)</th><th>Capacity (tonnes)</th></tr>
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
<h2>Reference comparison payload (JSON)</h2>
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

    for name, cfg in option_configs(base_cfg).items():
        ts_rows, summary = run_simulation(cfg)
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
    write_dataframe(ranking, run_dir / "ranking.csv")
    write_dataframe(option_rows, run_dir / "options.csv")
    write_summary({"ranking": ranking, "reference": OLD_MODEL_REFERENCE}, run_dir / "ranking.json")
    _build_optimization_html(ranking=ranking, option_rows=option_rows, model_comparison=OLD_MODEL_REFERENCE, run_dir=run_dir)
    return run_dir, ranking

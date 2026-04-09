from __future__ import annotations

import argparse
from pathlib import Path

from eaf_model.analysis.optimization import run_optimization
from eaf_model.analysis.sensitivity import run_sensitivity
from eaf_model.config import EAFConfig
from eaf_model.io.results import make_run_dir, write_dataframe, write_summary
from eaf_model.plotting.plots import plot_simulation
from eaf_model.simulation.core import run_simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Python EAF model workflows")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ("simulate", "sensitivity", "optimization"):
        p = sub.add_parser(name)
        p.add_argument("--output-dir", default="results", type=Path)
        p.add_argument("--time-secs", type=float, default=120.0)
        p.add_argument("--time-step", type=float, default=0.01)
        p.add_argument("--plot", action="store_true", default=True)
        p.add_argument("--no-plot", action="store_false", dest="plot")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    cfg = EAFConfig(total_time_s=args.time_secs, time_step_s=args.time_step)

    if args.cmd == "simulate":
        out = make_run_dir(args.output_dir, "simulation")
        df, summary = run_simulation(cfg)
        write_dataframe(df, out / "timeseries.csv")
        write_summary(summary, out / "summary.json")
        if args.plot:
            plot_simulation(df, out)
    elif args.cmd == "sensitivity":
        run_sensitivity(cfg, args.output_dir, make_plots=args.plot)
    elif args.cmd == "optimization":
        run_optimization(cfg, args.output_dir, make_plots=args.plot)


if __name__ == "__main__":
    main()

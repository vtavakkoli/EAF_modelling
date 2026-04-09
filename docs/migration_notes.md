# MATLAB → Python migration notes

## File mapping

- `eaf.m` → `src/eaf_model/simulation/*`, `src/eaf_model/cli.py`
- `Sensitivity/*.m` → `src/eaf_model/analysis/sensitivity.py`
- `Optimization/eaf_option*.m` → `src/eaf_model/analysis/optimization.py`
- MATLAB plotting sections → `src/eaf_model/plotting/plots.py`

## Scope preserved

- Time-marching dynamic EAF behavior with explicit Euler integration.
- Core thermo-chemical intent: FeO/C interactions, oxygen-driven carbon oxidation, MnO/C interaction, feed additions, off-gas venting, periodic takeout.
- KPI-style outputs (composition proxies, temperatures, gas ratio, volume and operating proxies).

## Approximations and deviations

- The original MATLAB model is very large (~1800 lines each script, mostly duplicated). The migration factors repeated script variants into a single configurable engine.
- Several highly coupled sub-models in MATLAB (detailed radiative view factors and some secondary reactions) are represented as reduced-order proxy terms to keep the model stable, testable, and maintainable.
- The optimization in MATLAB was scenario-based (`eaf_option1..4`). Python keeps this pattern and ranks scenarios with a documented weighted score.

## Validation notes

- Validation was performed as a best-effort structural equivalence check:
  - same categories of inputs and state variables,
  - stable evolution over time,
  - same classes of outputs/KPIs and plots,
  - sensitivity sweeps and option ranking workflows execute end-to-end.
- Exact numeric equivalence is not claimed.

## Known assumptions

- Time defaults were shortened for runtime ergonomics in CI/tests; CLI can restore longer runs with `--time-secs` and smaller `--time-step`.
- Physical bounds are enforced (`>= 0` masses and finite states).

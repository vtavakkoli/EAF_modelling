# EAF Modelling (Python 3.12 Migration)

## Python architecture

This repository now contains a fully Python-based Electric Arc Furnace (EAF) model. The original MATLAB model has been archived in `legacy_matlab/` for reference only and is no longer required for runtime.

## Python architecture

- `src/eaf_model/simulation/`: core dynamic model (mass transfer, heat transfer, chemistry, solver).
- `src/eaf_model/analysis/`: sensitivity and optimization workflows.
- `src/eaf_model/plotting/`: matplotlib plotting helpers.
- `src/eaf_model/io/`: standardized result writing and run metadata.
- `scripts/`: convenience scripts.
- `tests/`: smoke and workflow tests with `pytest`.

## Requirements

- Python **3.12+**
- `numpy`, `scipy`, `pandas`, `matplotlib`, `pytest`

## Install

```bash
pip install -r requirements.txt
pip install -e .
```

## Run workflows

### Simulation

```bash
python -m eaf_model.cli simulate
# or
python scripts/run_simulation.py simulate
```

### Sensitivity analysis

```bash
python -m eaf_model.cli sensitivity
# or
python scripts/run_sensitivity.py sensitivity
```

### Optimization

```bash
python -m eaf_model.cli optimization
# or
python scripts/run_optimization.py optimization
```

### Useful CLI options

- `--output-dir results`
- `--time-secs 120`
- `--time-step 0.01`
- `--plot` / `--no-plot`

## Results layout

Each run writes timestamped outputs:

- `results/simulation/<timestamp>/...`
- `results/sensitivity/<timestamp>/...`
- `results/optimization/<timestamp>/...`

Each run includes:

- `timeseries.csv` (or workflow summary CSV)
- `summary.json` / ranking JSON
- PNG plots
- metadata (timestamp, python version)

## Docker usage

Build and run using Python 3.12 containers:

```bash
docker compose up --build simulate
docker compose up --build sensitivity
docker compose up --build optimization
```

`results/` is bind-mounted so outputs are written to the host repository.

## Project structure

```text
.
├─ src/eaf_model/
├─ scripts/
├─ tests/
├─ docs/migration_notes.md
├─ legacy_matlab/original_matlab_files_for_reference_only/
├─ Images/
├─ EAF_modelling_report.pdf
├─ pyproject.toml
├─ requirements.txt
├─ Dockerfile
└─ docker-compose.yml
```

## Migration notes and limitations

- The Python model keeps explicit fixed-step integration behavior and key KPI definitions used by the MATLAB implementation.
- The MATLAB scripts under Sensitivity and Optimization were consolidated into parameterized Python workflows.
- See `docs/migration_notes.md` for mapping and assumptions.

## Legacy MATLAB files

All original `.m` files are preserved under `legacy_matlab/original_matlab_files_for_reference_only/` for audit/reference only.

from eaf_model.analysis.sensitivity import run_sensitivity
from eaf_model.config import EAFConfig


def test_sensitivity_creates_output(tmp_path) -> None:
    run_dir, rows = run_sensitivity(EAFConfig(total_time_s=5.0, time_step_s=0.05), tmp_path, make_plots=False)
    assert run_dir.exists()
    assert len(rows) > 0
    assert (run_dir / "sensitivity_summary.csv").exists()
    assert (run_dir / "sensitivity.html").exists()

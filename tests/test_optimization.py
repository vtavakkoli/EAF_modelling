from eaf_model.analysis.optimization import run_optimization
from eaf_model.config import EAFConfig


def test_optimization_creates_ranking_and_html(tmp_path) -> None:
    run_dir, ranking = run_optimization(EAFConfig(total_time_s=8.0, time_step_s=0.05), tmp_path, make_plots=False)
    assert run_dir.exists()
    assert len(ranking) > 0
    assert (run_dir / "ranking.csv").exists()
    assert (run_dir / "optimization.html").exists()

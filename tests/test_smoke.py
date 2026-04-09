from eaf_model import EAFConfig


def test_import() -> None:
    cfg = EAFConfig()
    assert cfg.total_time_s > 0

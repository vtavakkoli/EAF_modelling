from __future__ import annotations

import csv
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def make_run_dir(base: Path, workflow: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = base / workflow / stamp
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_dataframe(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary(summary: dict[str, Any], path: Path) -> None:
    enriched = {
        **summary,
        "metadata": {
            "python_version": platform.python_version(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
    }
    path.write_text(json.dumps(enriched, indent=2), encoding="utf-8")

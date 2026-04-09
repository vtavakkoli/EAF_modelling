from __future__ import annotations

from pathlib import Path


def plot_simulation(rows: list[dict[str, float]], out_dir: Path) -> list[Path]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        note = out_dir / "plots_skipped.txt"
        note.write_text("matplotlib not installed; plotting skipped", encoding="utf-8")
        return [note]

    t = [r["time_s"] for r in rows]
    files: list[Path] = []

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(t, [r["t_liquid_metal_k"] for r in rows], label="Liquid metal")
    ax.plot(t, [r["t_liquid_slag_k"] for r in rows], label="Liquid slag")
    ax.plot(t, [r["t_gas_k"] for r in rows], label="Gas")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Temperature [K]")
    ax.legend()
    p = out_dir / "temperatures.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    files.append(p)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(t, [r["m_liquid_metal_kg"] for r in rows], label="Liquid metal")
    ax.plot(t, [r["m_solid_kg"] for r in rows], label="Solid")
    ax.plot(t, [r["m_liquid_slag_kg"] for r in rows], label="Liquid slag")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Mass [kg]")
    ax.legend()
    p = out_dir / "masses.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    files.append(p)

    return files

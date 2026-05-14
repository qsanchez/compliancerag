import base64
import io
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless — no display required
import matplotlib.pyplot as plt


def _detect_axes(rows: list[dict]) -> tuple[str, str, str]:
    """Return (chart_type, x_col, y_col) for the first plottable column pair."""
    columns = list(rows[0].keys())
    numeric_cols, label_cols, year_cols = [], [], []

    for col in columns:
        samples = [r[col] for r in rows[:5] if r.get(col) not in (None, "")]
        try:
            vals = [float(v) for v in samples]
            # Year-like integers are x-axis labels, not metrics
            if all(v == int(v) and 1990 <= int(v) <= 2100 for v in vals):
                year_cols.append(col)
            else:
                numeric_cols.append(col)
        except (ValueError, TypeError):
            label_cols.append(col)

    if not numeric_cols:
        raise ValueError("No numeric column found for chart")

    y_col = numeric_cols[0]

    if year_cols:
        rows.sort(key=lambda r: int(r.get(year_cols[0], 0)))
        return "line", year_cols[0], y_col

    x_col = label_cols[0] if label_cols else columns[0]
    return "bar", x_col, y_col


def generate_chart(metrics_result: dict) -> str | None:
    rows: list[dict[str, Any]] = metrics_result.get("rows", [])
    if not rows:
        return None

    try:
        chart_type, x_col, y_col = _detect_axes(rows)
    except ValueError:
        return None

    x_vals = [str(r.get(x_col, "")) for r in rows]
    y_vals = [float(r.get(y_col) or 0) for r in rows]

    fig, ax = plt.subplots(figsize=(10, 5))

    if chart_type == "line":
        ax.plot(x_vals, y_vals, marker="o", linewidth=2, color="#2563eb")
        ax.fill_between(range(len(x_vals)), y_vals, alpha=0.08, color="#2563eb")
        ax.set_xticks(range(len(x_vals)))
        ax.set_xticklabels(x_vals, rotation=45, ha="right")
    else:
        ax.bar(range(len(x_vals)), y_vals, color="#2563eb", alpha=0.85)
        ax.set_xticks(range(len(x_vals)))
        ax.set_xticklabels(x_vals, rotation=45, ha="right")

    ax.set_xlabel(x_col.replace("_", " ").title())
    ax.set_ylabel(y_col.replace("_", " ").title())
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

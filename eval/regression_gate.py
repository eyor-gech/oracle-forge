from __future__ import annotations

from typing import Dict, Any


def evaluate_regression_gate(current_pass_at_1: float, baseline_pass_at_1: float, max_drop: float = 0.02) -> Dict[str, Any]:
    """Evaluate regression gate status.

    Inputs:
    - current_pass_at_1: current run pass@1
    - baseline_pass_at_1: baseline pass@1
    - max_drop: tolerated absolute drop before failing gate

    Outputs:
    - dict with gate status, delta, and summary message
    """
    delta = float(current_pass_at_1) - float(baseline_pass_at_1)
    failed = delta < -abs(max_drop)
    return {
        "passed": not failed,
        "delta": round(delta, 6),
        "threshold": -abs(max_drop),
        "message": (
            f"Regression gate failed: pass@1 dropped by {abs(delta):.4f} (> {max_drop:.4f})"
            if failed
            else f"Regression gate passed: pass@1 delta {delta:.4f}"
        ),
    }


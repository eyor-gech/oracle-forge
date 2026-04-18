from __future__ import annotations

import math
from typing import Tuple


def wilson_ci(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """Compute Wilson score confidence interval.

    Inputs:
    - successes: number of successful trials
    - total: total number of Bernoulli trials
    - z: z-score (default 1.96 for 95% CI)

    Outputs:
    - (lower_bound, upper_bound)

    Assumptions:
    - `total` can be zero; returns (0.0, 0.0) in that case.
    """
    if total <= 0:
        return 0.0, 0.0

    phat = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    center = phat + z2 / (2.0 * total)
    margin = z * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * total)) / total)

    lower = (center - margin) / denominator
    upper = (center + margin) / denominator
    return max(0.0, lower), min(1.0, upper)


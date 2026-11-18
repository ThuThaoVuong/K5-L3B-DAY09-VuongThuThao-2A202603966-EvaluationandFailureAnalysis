"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class

def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have the same length")

    tp = fp = fn = tn = 0

    for h, j in zip(human, judge):
        h = h.strip().upper()
        j = j.strip().upper()

        if h not in {"PASS", "FAIL"} or j not in {"PASS", "FAIL"}:
            raise ValueError("labels must be PASS or FAIL")

        if h == POS and j == POS:
            tp += 1
        elif h != POS and j == POS:
            fp += 1
        elif h == POS and j != POS:
            fn += 1
        else:
            tn += 1

    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def precision_recall(
    human: Sequence[str], judge: Sequence[str]
) -> tuple[float, float]:
    """Precision = tp/(tp+fp), recall = tp/(tp+fn)."""
    cm = confusion(human, judge)

    tp = cm["tp"]
    fp = cm["fp"]
    fn = cm["fn"]

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0

    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """Cohen's kappa; raise ValueError when expected agreement is 1."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have the same length")

    if not human:
        raise ValueError("labels must not be empty")

    cm = confusion(human, judge)
    n = len(human)

    # Observed agreement
    p_o = (cm["tp"] + cm["tn"]) / n

    # Actual and predicted proportions of FAIL
    actual_fail = (cm["tp"] + cm["fn"]) / n
    predicted_fail = (cm["tp"] + cm["fp"]) / n

    actual_pass = 1 - actual_fail
    predicted_pass = 1 - predicted_fail

    # Expected agreement by chance
    p_e = (
        actual_fail * predicted_fail
        + actual_pass * predicted_pass
    )

    if p_e == 1:
        raise ValueError("Cohen's kappa is undefined when p_e == 1")

    return (p_o - p_e) / (1 - p_e)


def rogan_gladen(
    observed_rate: float,
    sensitivity: float,
    specificity: float
) -> float:
    """Correct observed failure rate for judge error; clip to [0, 1]."""
    denominator = sensitivity + specificity - 1

    if denominator <= 0:
        raise ValueError("sensitivity + specificity must be greater than 1")

    corrected = (observed_rate + specificity - 1) / denominator

    return max(0.0, min(1.0, corrected))



def paired_bootstrap(
    a: Sequence[float],
    b: Sequence[float],
    *,
    n_resamples: int = 1000,
    rng: int = 2027,
    confidence: float = 0.95
) -> tuple[float, float, float]:
    """Paired percentile bootstrap for the mean difference a - b."""

    import numpy as np
    from scipy.stats import bootstrap

    if len(a) != len(b):
        raise ValueError("a and b must have the same length")

    if len(a) == 0:
        raise ValueError("a and b must not be empty")

    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")

    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)

    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("a and b must contain finite values")

    if np.array_equal(a, b):
        return (0.0, 0.0, 0.0)

    def statistic(x, y):
        return np.mean(x - y)

    result = bootstrap(
        (a, b),
        statistic,
        paired=True,
        vectorized=False,
        n_resamples=n_resamples,
        confidence_level=confidence,
        method="percentile",
        rng=np.random.default_rng(rng),
    )

    difference = float(np.mean(a) - np.mean(b))
    lower = float(result.confidence_interval.low)
    upper = float(result.confidence_interval.high)

    return difference, lower, upper



def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    # TODO M6
    raise NotImplementedError


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    # TODO M6
    raise NotImplementedError

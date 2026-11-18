"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item



def integrity_check(
    pr: dict,
    base: dict,
    spec: dict,
    base_spec: dict | None = None
) -> list[str]:
    """Reject corrupted reports and weakened metric specifications."""

    import math

    problems = []

    # 1. Validate report structure.
    manifest = pr.get("manifest") or {}
    rows = pr.get("rows")

    if not isinstance(rows, list) or not rows:
        return ["report has no valid rows"]

    seeds = manifest.get("seeds") or []
    items = manifest.get("items")

    if not isinstance(items, int) or items <= 0:
        problems.append("invalid manifest item count")

    if not seeds or len(seeds) != len(set(seeds)):
        problems.append("invalid or duplicated manifest seeds")

    # 2. Check expected row count.
    if isinstance(items, int) and items > 0 and seeds:
        expected_count = items * len(seeds)

        if len(rows) != expected_count:
            problems.append(
                f"row count mismatch: {len(rows)} != {expected_count}"
            )

    # 3. Check duplicate (item_id, seed).
    def row_keys(report):
        return [
            (r.get("item_id"), r.get("seed"))
            for r in report.get("rows", [])
        ]

    keys = row_keys(pr)

    if len(keys) != len(set(keys)):
        problems.append("duplicate (item_id, seed) rows")

    # 4. Check PR and baseline have identical evaluation cases.
    base_keys = row_keys(base)

    if set(keys) != set(base_keys):
        problems.append("PR item/seed set differs from baseline")

    # 5. Check non-finite metric values.
    metrics = pr.get("metrics") or {}

    for name, value in metrics.items():
        if isinstance(value, float) and not math.isfinite(value):
            problems.append(f"non-finite metric: {name}")

    # 6. Evaluator failures must never be ignored.
    if pr.get("evaluator_failures"):
        problems.append("evaluator failures present")

    # 7. A graded metric cannot silently disappear as None.
    for metric in spec.get("metrics", []):
        mid = metric["id"]

        if mid not in metrics:
            problems.append(f"missing aggregate metric: {mid}")

        # Derived metrics are aggregate-only.
        if any(mid in row for row in rows):
            for index, row in enumerate(rows):
                if mid not in row:
                    problems.append(
                        f"missing row metric: {mid} at row {index}"
                    )
                    break

                if row[mid] is None:
                    problems.append(
                        f"None grader result: {mid} at row {index}"
                    )
                    break

    # 8. Slice labels must not be changed between PR and baseline.
    def slice_map(report):
        result = {}

        for row in report.get("rows", []):
            item_id = row.get("item_id")
            tags = tuple(sorted(row.get("slices") or []))

            if item_id in result and result[item_id] != tags:
                result[item_id] = None
            else:
                result[item_id] = tags

        return result

    if slice_map(pr) != slice_map(base):
        problems.append("slice tags differ from baseline")

    # 9. Ratchet: same eval-set version cannot weaken the spec.
    if base_spec is not None:
        same_version = (
            spec.get("eval_set_version")
            == base_spec.get("eval_set_version")
        )

        if same_version:
            old_metrics = {
                m["id"]: m for m in base_spec.get("metrics", [])
            }

            new_metrics = {
                m["id"]: m for m in spec.get("metrics", [])
            }

            for mid, old in old_metrics.items():
                new = new_metrics.get(mid)

                if new is None:
                    problems.append(f"metric removed: {mid}")
                    continue

                old_th = old.get("threshold") or {}
                new_th = new.get("threshold") or {}

                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"blocking weakened: {mid}")

                if (
                    "min" in old_th
                    and (
                        "min" not in new_th
                        or new_th["min"] < old_th["min"]
                    )
                ):
                    problems.append(f"minimum threshold weakened: {mid}")

                if (
                    "max" in old_th
                    and (
                        "max" not in new_th
                        or new_th["max"] > old_th["max"]
                    )
                ):
                    problems.append(f"maximum threshold weakened: {mid}")

                if (
                    old_th.get("no_significant_drop")
                    and not new_th.get("no_significant_drop")
                ):
                    problems.append(
                        f"no_significant_drop removed: {mid}"
                    )

            # 10. Ratchet for slices.
            old_slices = {
                s["name"]: s for s in base_spec.get("slices", [])
            }

            new_slices = {
                s["name"]: s for s in spec.get("slices", [])
            }

            for name, old in old_slices.items():
                new = new_slices.get(name)

                if new is None:
                    problems.append(f"slice removed: {name}")
                    continue

                if old.get("metric") != new.get("metric"):
                    problems.append(f"slice metric changed: {name}")

                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"slice blocking weakened: {name}")

                if (
                    "min" in old
                    and (
                        "min" not in new
                        or new["min"] < old["min"]
                    )
                ):
                    problems.append(f"slice minimum weakened: {name}")

                if (
                    old.get("no_significant_drop")
                    and not new.get("no_significant_drop")
                ):
                    problems.append(
                        f"slice no_significant_drop removed: {name}"
                    )

    return sorted(set(problems))


def slice_check(
    pr: dict,
    base: dict,
    spec: dict
) -> tuple[list[str], list[str]]:
    """Check capability regressions inside important slices."""

    blocked = []
    lines = []

    bs = spec.get("bootstrap", {})

    for item in spec.get("slices", []):
        name = item["name"]
        metric = item["metric"]

        current = per_item(pr, metric, name)
        baseline = per_item(base, metric, name)

        values = list(current.values())

        if not values:
            value = None
        else:
            value = sum(values) / len(values)

        verdict = "ok"
        notes = []

        # 1. Missing slice evidence.
        if value is None:
            verdict = "missing"
            notes.append("no PR observations")

        # 2. Absolute minimum threshold.
        if value is not None and "min" in item:
            if value < item["min"]:
                verdict = "fail"
                notes.append(
                    f"value {value:.3f} < floor {item['min']:.3f}"
                )

        # 3. Paired bootstrap against baseline.
        if item.get("no_significant_drop"):
            keys = sorted(set(current) & set(baseline))

            if not keys:
                verdict = "fail"
                notes.append("no paired baseline observations")
            else:
                delta, lower, upper = stats.paired_bootstrap(
                    [current[k] for k in keys],
                    [baseline[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000),
                    rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95)
                )

                notes.append(
                    f"delta={delta:+.3f}, "
                    f"CI=[{lower:+.3f}, {upper:+.3f}]"
                )

                if upper < 0:
                    verdict = "fail"

        label = f"slice:{name}/{metric}"

        if verdict != "ok" and item.get("blocking", False):
            blocked.append(label)
            status = "BLOCK"
        elif verdict != "ok":
            status = "WARN"
        else:
            status = "ok"

        lines.append(
            f"  {label:<36} "
            f"{str(value):<10} "
            f"{'; '.join(notes):<55} "
            f"{status}"
        )

    return blocked, lines




def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): detect regressions hidden by aggregate averages."""

    blocked = []
    lines = []

    bs = spec.get("bootstrap", {})
    n_resamples = bs.get("n_resamples", 1000)
    rng = bs.get("rng", 2027)
    confidence = bs.get("confidence", 0.95)

    for item in spec.get("slices", []):
        name = item["name"]
        metric = item["metric"]
        blocking = item.get("blocking", False)

        # Get per-item averages within this slice.
        current = per_item(pr, metric, slice_name=name)
        baseline = per_item(base, metric, slice_name=name)

        label = f"slice:{name}/{metric}"
        notes = []
        verdict = "ok"

        # 1. Calculate the mean of the PR slice.
        if not current:
            value = None
            verdict = "missing"
            notes.append("no PR observations")
        else:
            value = sum(current.values()) / len(current)

        # 2. Check the absolute minimum threshold.
        minimum = item.get("min")

        if value is not None and minimum is not None:
            if value < minimum:
                verdict = "fail"
                notes.append(
                    f"value {value:.3f} < min {minimum:.3f}"
                )

        # 3. Paired bootstrap against the baseline.
        if item.get("no_significant_drop"):
            keys = sorted(set(current) & set(baseline))

            if not keys:
                verdict = "missing"
                notes.append("no paired observations")
            else:
                delta, lower, upper = stats.paired_bootstrap(
                    [current[k] for k in keys],
                    [baseline[k] for k in keys],
                    n_resamples=n_resamples,
                    rng=rng,
                    confidence=confidence,
                )

                notes.append(
                    f"delta={delta:+.3f} "
                    f"CI=[{lower:+.3f}, {upper:+.3f}]"
                )

                # CI entirely below zero means significant regression.
                if upper < 0:
                    verdict = "fail"

        # 4. Record blocking decision.
        if verdict != "ok" and blocking:
            blocked.append(label)
            status = "BLOCK"
        elif verdict != "ok":
            status = "WARN"
        else:
            status = "ok"

        # 5. Add report line.
        value_text = "N/A" if value is None else f"{value:.3f}"

        lines.append(
            f"  {label:<36} "
            f"{value_text:<10} "
            f"{'; '.join(notes):<55} "
            f"{status}"
        )

    return blocked, lines



def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

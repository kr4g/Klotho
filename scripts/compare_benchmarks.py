#!/usr/bin/env python
"""
Compare before/after benchmark results.

Usage:
  python scripts/compare_benchmarks.py [before.json] [after.json]
  python scripts/compare_benchmarks.py   # uses benchmarks/before_pt.json vs benchmarks/after_pt.json
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BEFORE = REPO / "benchmarks" / "before_pt.json"
DEFAULT_AFTER = REPO / "benchmarks" / "after_pt.json"


def main():
    before_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BEFORE
    after_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_AFTER

    with open(before_path) as f:
        before = json.load(f)
    with open(after_path) as f:
        after = json.load(f)

    all_keys = sorted(set(before) | set(after))
    print(f"ParameterTree benchmark: BEFORE vs AFTER")
    print(f"  Before: {before_path.name}")
    print(f"  After:  {after_path.name}")
    print("=" * 85)
    print(f'  {"Operation":<42} {"Before (ms)":>12} {"After (ms)":>12} {"Δ %":>10}')
    print("-" * 85)
    for key in all_keys:
        b = before.get(key, {})
        a = after.get(key, {})
        bm = b.get("mean_ms")
        am = a.get("mean_ms")
        if bm is not None and am is not None:
            pct = ((am - bm) / bm * 100) if bm else 0
            sign = "+" if pct > 0 else ""
            print(f"  {key:<42} {bm:>8.3f} ± {b.get('stdev_ms',0):<4.3f} {am:>8.3f} ± {a.get('stdev_ms',0):<4.3f} {sign}{pct:>7.1f}%")
        elif bm is not None:
            print(f"  {key:<42} {bm:>8.3f} ± {b.get('stdev_ms',0):<4.3f} {'(N/A)':>12} {'(removed)':>10}")
        else:
            print(f"  {key:<42} {'(N/A)':>12} {am:>8.3f} ± {a.get('stdev_ms',0):<4.3f} {'(new)':>10}")
    print("=" * 85)


if __name__ == "__main__":
    main()

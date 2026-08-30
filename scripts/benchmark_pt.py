#!/usr/bin/env python
"""
Benchmark ParameterTree / UC operations: set_pfields, get_pfield, event iteration.

Usage:
  python scripts/benchmark_pt.py [--runs N] [--warmup N]
  python scripts/benchmark_pt.py --save PATH   # save results to JSON for before/after
  python scripts/benchmark_pt.py --compare     # run current vs origin/main

Reports mean ± stdev in milliseconds. Use --save to capture baseline before optimizations.
"""
import sys
import time
import statistics
import argparse
import subprocess
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from klotho.thetos import CompositionalUnit as UC, ToneInstrument as ToneInst


def _benchmark(name, func, n_runs=50, n_warmup=5):
    for _ in range(n_warmup):
        func()
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        func()
        times.append((time.perf_counter() - t0) * 1000)
    mean = statistics.mean(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0
    return mean, stdev


def run_benchmarks(n_runs=50, n_warmup=5):
    results = {}

    def bench_uc_init_simple():
        UC(tempus="4/4", prolatio=(1, 1, 1, 1), beat="1/4", bpm=120, inst=ToneInst.Kalimba())

    results["UC init (4 leaves)"] = _benchmark(
        "uc_init_simple", bench_uc_init_simple, n_runs, n_warmup
    )

    def bench_set_pfields_root():
        uc = UC(
            tempus="4/4",
            prolatio=tuple((1,) * 32),
            beat="1/4",
            bpm=120,
            inst=ToneInst.Kalimba(),
        )
        uc.set_pfields(0, freq=440, vel=0.8)

    results["set_pfields(root) → 32 leaves"] = _benchmark(
        "set_pfields_root", bench_set_pfields_root, n_runs, n_warmup
    )

    def bench_set_pfields_per_leaf():
        uc = UC(
            tempus="4/4",
            prolatio=tuple((1,) * 32),
            beat="1/4",
            bpm=120,
            inst=ToneInst.Kalimba(),
        )
        for i, leaf in enumerate(uc.rt.leaf_nodes):
            uc.set_pfields(leaf, freq=261 + i, vel=0.5 + i * 0.01)

    results["set_pfields(per leaf) × 32"] = _benchmark(
        "set_pfields_per_leaf", bench_set_pfields_per_leaf, n_runs, n_warmup
    )

    uc = UC(
        tempus="4/4",
        prolatio=tuple((1,) * 32),
        beat="1/4",
        bpm=120,
        inst=ToneInst.Kalimba(),
    )
    uc.set_pfields(0, freq=440, vel=0.8)

    def bench_get_pfield_many():
        for leaf in uc.rt.leaf_nodes:
            _ = uc.get_pfield(leaf, "freq")
            _ = uc.get_pfield(leaf, "vel")

    results["get_pfield × 64 (32 leaves × 2 keys)"] = _benchmark(
        "get_pfield_many", bench_get_pfield_many, n_runs, n_warmup
    )

    def bench_events_simple():
        uc = UC(
            tempus="4/4",
            prolatio=tuple((1,) * 32),
            beat="1/4",
            bpm=120,
            inst=ToneInst.Kalimba(),
        )
        uc.set_pfields(0, freq=440)
        _ = list(uc)

    results["events (32 leaves, 1 pfield)"] = _benchmark(
        "events_simple", bench_events_simple, n_runs, n_warmup
    )

    S1 = ((20, ((5, (1,) * 5),) * 4), (15, ((3, (1,) * 3),) * 5))

    def bench_events_complex():
        uc = UC(
            tempus="36/16",
            prolatio=S1,
            beat="1/8",
            bpm=184,
            inst=ToneInst.Kalimba(),
        )
        limbs = uc.rt.at_depth(1)
        uc.set_mfields(limbs[0], idx=0, drct=1)
        uc.set_mfields(limbs[1], idx=7, drct=-1)
        for branch in uc.rt.at_depth(2):
            for leaf in uc.rt.subtree_leaves(branch):
                uc.set_pfields(leaf, freq=440)
        _ = list(uc)

    results["events (35 leaves, mfields+pfields)"] = _benchmark(
        "events_complex", bench_events_complex, n_runs, n_warmup
    )

    return results


def main():
    ap = argparse.ArgumentParser(description="Benchmark ParameterTree/UC operations")
    ap.add_argument("--runs", type=int, default=100, help="Timed runs per operation")
    ap.add_argument("--warmup", type=int, default=10, help="Warmup runs before timing")
    ap.add_argument("--compare", action="store_true", help="Compare current vs origin/main")
    ap.add_argument("--save", type=str, metavar="PATH", help="Save results to JSON file")
    args = ap.parse_args()

    if args.compare:
        return run_compare(args.runs, args.warmup)

    print("ParameterTree / UC benchmark (current)")
    print("=" * 60)
    results = run_benchmarks(n_runs=args.runs, n_warmup=args.warmup)
    for name, (mean, stdev) in results.items():
        print(f"  {name:40} {mean:8.3f} ± {stdev:6.3f} ms")
    print("=" * 60)

    if args.save:
        out = {k: {"mean_ms": v[0], "stdev_ms": v[1]} for k, v in results.items()}
        Path(args.save).parent.mkdir(parents=True, exist_ok=True)
        with open(args.save, "w") as f:
            json.dump(out, f, indent=2)
        print(f"Saved to {args.save}")

    return results


def run_compare(n_runs, n_warmup):
    repo = Path(__file__).resolve().parent.parent
    pt_path = repo / "klotho" / "thetos" / "parameters" / "parameter_tree.py"
    comp_path = repo / "klotho" / "thetos" / "composition" / "compositional.py"

    def run_bench():
        out = subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "benchmark_pt.py"),
                "--runs",
                str(n_runs),
                "--warmup",
                str(n_warmup),
            ],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if out.returncode != 0:
            print("Benchmark failed:", out.stderr)
            return {}
        import re

        lines = [l for l in out.stdout.splitlines() if "±" in l]
        results = {}
        pat = re.compile(r"^\s*(.+?)\s+([\d.]+)\s+±\s+([\d.]+)\s+ms\s*$")
        for line in lines:
            m = pat.match(line)
            if m:
                name = re.sub(r"\s+", " ", m.group(1).strip())
                mean = float(m.group(2))
                stdev = float(m.group(3))
                results[name] = (mean, stdev)
        return results

    print("Running benchmark: CURRENT (local changes)...")
    current = run_bench()

    print("Stashing local changes, switching to origin/main...")
    subprocess.run(
        ["git", "stash", "push", "-m", "benchmark_pt", "--", str(pt_path), str(comp_path)],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "origin/main", "--", str(pt_path), str(comp_path)],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    print("Running benchmark: REMOTE (origin/main)...")
    remote = run_bench()
    print("Restoring local changes...")
    subprocess.run(["git", "stash", "pop"], cwd=repo, check=True, capture_output=True)

    all_keys = sorted(set(current) | set(remote))
    print()
    print("ParameterTree benchmark: CURRENT vs REMOTE (origin/main)")
    print("=" * 80)
    print(f'  {"Operation":<42} {"Current (ms)":>12} {"Remote (ms)":>12} {"Δ %":>8}')
    print("-" * 80)
    for key in all_keys:
        c = current.get(key, (None, None))
        r = remote.get(key, (None, None))
        cm, cs = c
        rm, rs = r
        if cm is not None and rm is not None:
            pct = ((cm - rm) / rm * 100) if rm else 0
            sign = "+" if pct > 0 else ""
            print(f"  {key:<42} {cm:>8.3f} ± {cs:<5.3f} {rm:>8.3f} ± {rs:<5.3f} {sign}{pct:>6.1f}%")
        elif cm is not None:
            print(f"  {key:<42} {cm:>8.3f} ± {cs:<5.3f} {'(N/A)':>12} {'(new)':>8}")
        else:
            print(f"  {key:<42} {'(N/A)':>12} {rm:>8.3f} ± {rs:<5.3f} {'(removed)':>8}")
    print("=" * 80)


if __name__ == "__main__":
    main()

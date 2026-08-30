#!/usr/bin/env python
"""
Benchmark RhythmTree operations: current (local) vs origin/main (remote).

Usage:
  python scripts/benchmark_rt.py [--runs N] [--warmup N]
  python scripts/benchmark_rt.py --compare   # run both versions, report delta

Reports mean ± stdev in milliseconds for each operation.
"""
import sys
import time
import statistics
import argparse
import subprocess
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from klotho.chronos.rhythm_trees import RhythmTree


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

    def bench_init_simple():
        RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))

    results['init (4 leaves)'] = _benchmark('init_simple', bench_init_simple, n_runs, n_warmup)

    def bench_init_deep():
        RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1, 1)), (1, (1, 1)), (1, (1, 1, 1, 1))))

    results['init (nested, 9 leaves)'] = _benchmark('init_deep', bench_init_deep, n_runs, n_warmup)

    def bench_init_large():
        RhythmTree(span=1, meas='4/4', subdivisions=tuple((1,) * 16))

    results['init (16 leaves)'] = _benchmark('init_large', bench_init_large, n_runs, n_warmup)

    rt = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1, 1)), (1, (1, 1)), (1, (1, 1, 1, 1))))
    leaf = next(n for n in rt.leaf_nodes)
    sub = rt.subtree(2, renumber=True)

    def bench_graft():
        rt_copy = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1, 1)), (1, (1, 1)), (1, (1, 1, 1, 1))))
        rt_copy.graft_subtree(leaf, sub, mode='replace')

    results['graft_subtree'] = _benchmark('graft', bench_graft, n_runs, n_warmup)

    def bench_make_rest():
        rt_copy = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1, 1)), (1, (1, 1)), (1, (1, 1, 1, 1))))
        rt_copy.make_rest(1)

    results['make_rest'] = _benchmark('make_rest', bench_make_rest, n_runs, n_warmup)

    if hasattr(RhythmTree, 'subdivide'):
        def bench_subdivide():
            rt_copy = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
            leaf = next(n for n in rt_copy.leaf_nodes)
            rt_copy.subdivide(leaf, (1, 1, 1))
        results['subdivide'] = _benchmark('subdivide', bench_subdivide, n_runs, n_warmup)

    if hasattr(RhythmTree, 'prune'):
        def bench_prune():
            rt_copy = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1, 1)), (1, (1, 1)), (1, (1, 1, 1, 1))))
            rt_copy.prune(next(n for n in rt_copy.leaf_nodes))
        results['prune'] = _benchmark('prune', bench_prune, n_runs, n_warmup)

    if hasattr(RhythmTree, 'remove_subtree'):
        def bench_remove_subtree():
            rt_copy = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1, 1)), (1, (1, 1)), (1, (1, 1, 1, 1))))
            rt_copy.remove_subtree(2)
        results['remove_subtree'] = _benchmark('remove_subtree', bench_remove_subtree, n_runs, n_warmup)

    def bench_durations_large():
        rt = RhythmTree(span=1, meas='4/4', subdivisions=tuple((1,) * 64))
        _ = rt.durations

    results['durations (64 leaves)'] = _benchmark('durations', bench_durations_large, n_runs, n_warmup)

    if hasattr(RhythmTree, 'subdivide'):
        def bench_subdivide_on_large_tree():
            rt = RhythmTree(span=1, meas='4/4', subdivisions=tuple((1,) * 32))
            leaf = next(n for n in rt.leaf_nodes)
            rt.subdivide(leaf, (1, 1, 1))
        results['subdivide (on 32-leaf tree)'] = _benchmark(
            'subdivide_large', bench_subdivide_on_large_tree, n_runs, n_warmup
        )

    return results


def main():
    ap = argparse.ArgumentParser(description='Benchmark RhythmTree operations')
    ap.add_argument('--runs', type=int, default=100, help='Number of timed runs per operation')
    ap.add_argument('--warmup', type=int, default=10, help='Warmup runs before timing')
    ap.add_argument('--compare', action='store_true', help='Compare current vs origin/main')
    ap.add_argument('--save', type=str, metavar='PATH', help='Save results to JSON file')
    args = ap.parse_args()

    if args.compare:
        return run_compare(args.runs, args.warmup)

    print('RhythmTree benchmark (current)')
    print('=' * 60)
    results = run_benchmarks(n_runs=args.runs, n_warmup=args.warmup)
    for name, (mean, stdev) in results.items():
        print(f'  {name:35} {mean:8.3f} ± {stdev:6.3f} ms')
    print('=' * 60)

    if args.save:
        out = {k: {'mean_ms': v[0], 'stdev_ms': v[1]} for k, v in results.items()}
        Path(args.save).parent.mkdir(parents=True, exist_ok=True)
        with open(args.save, 'w') as f:
            json.dump(out, f, indent=2)
        print(f'Saved to {args.save}')

    return results


def run_compare(n_runs, n_warmup):
    repo = Path(__file__).resolve().parent.parent
    rt_path = repo / 'klotho' / 'chronos' / 'rhythm_trees' / 'rhythm_tree.py'
    tree_path = repo / 'klotho' / 'topos' / 'graphs' / 'trees' / 'trees.py'

    def run_bench():
        out = subprocess.run(
            [sys.executable, str(repo / 'scripts' / 'benchmark_rt.py'),
             '--runs', str(n_runs), '--warmup', str(n_warmup)],
            cwd=repo, capture_output=True, text=True
        )
        if out.returncode != 0:
            print('Benchmark failed:', out.stderr)
            return {}
        import re
        lines = [l for l in out.stdout.splitlines() if '±' in l]
        results = {}
        pat = re.compile(r'^\s*(.+?)\s+([\d.]+)\s+±\s+([\d.]+)\s+ms\s*$')
        for line in lines:
            m = pat.match(line)
            if m:
                name = re.sub(r'\s+', ' ', m.group(1).strip())
                mean = float(m.group(2))
                stdev = float(m.group(3))
                results[name] = (mean, stdev)
        return results

    print('Running benchmark: CURRENT (local changes)...')
    current = run_bench()

    print('Stashing local changes, switching to origin/main...')
    subprocess.run(['git', 'stash', 'push', '-m', 'benchmark', '--', str(rt_path), str(tree_path)],
                   cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ['git', 'checkout', 'origin/main', '--', str(rt_path), str(tree_path)],
        cwd=repo, check=True, capture_output=True
    )
    print('Running benchmark: REMOTE (origin/main)...')
    remote = run_bench()
    print('Restoring local changes...')
    subprocess.run(['git', 'stash', 'pop'], cwd=repo, check=True, capture_output=True)

    all_keys = sorted(set(current) | set(remote))
    print()
    print('RhythmTree benchmark: CURRENT vs REMOTE (origin/main)')
    print('=' * 75)
    print(f'  {"Operation":<38} {"Current (ms)":>12} {"Remote (ms)":>12} {"Δ %":>8}')
    print('-' * 75)
    for key in all_keys:
        c = current.get(key, (None, None))
        r = remote.get(key, (None, None))
        cm, cs = c
        rm, rs = r
        if cm is not None and rm is not None:
            pct = ((cm - rm) / rm * 100) if rm else 0
            sign = '+' if pct > 0 else ''
            print(f'  {key:<38} {cm:>8.3f} ± {cs:<5.3f} {rm:>8.3f} ± {rs:<5.3f} {sign}{pct:>6.1f}%')
        elif cm is not None:
            print(f'  {key:<38} {cm:>8.3f} ± {cs:<5.3f} {"(N/A)":>12} {"(new)":>8}')
        else:
            print(f'  {key:<38} {"(N/A)":>12} {rm:>8.3f} ± {rs:<5.3f} {"(removed)":>8}')
    print('=' * 75)
    print()
    print('Note: Remote prune/remove_subtree do not call _evaluate (faster but leave RT inconsistent).')
    print('      Current version re-evaluates from minimal scope after mutations.')


if __name__ == '__main__':
    main()

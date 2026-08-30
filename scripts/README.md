# `scripts/` — developer tooling

Not part of the installed package. `setup.py` uses `find_packages()`, which
needs an `__init__.py`; there isn't one here, and `MANIFEST.in` only recurses
into `klotho/`, so nothing in this directory reaches the wheel or PyPI.

This directory was blanket-ignored until 2026-08-30. It is tracked now because
the capture scripts below *are* the provenance of the test oracles — a fixture
whose capture procedure is invisible cannot be audited by anyone but its author.

## Oracle capture — read `tests/README.md` first

These four write the files that tests compare against. **Every one refuses to
run without `KLOTHO_ALLOW_REGEN=1`**, because an oracle regenerated from the
working tree stops being independent of the code it checks, and every test that
reads it silently loses the ability to fail. That is not hypothetical: it was
measured against this repo on 2026-08-29.

| Script | Writes | Capture rule |
|---|---|---|
| `capture_haddad_figures.py` | `tests/fixtures/haddad_figures.json` | Reads the thesis PDF. Never imports `klotho` at all — that is the point. |
| `capture_expected_trees.py` | `tests/expected_trees.json` | Must run against a **reference build**, not this tree. Enforced. |
| `capture_expected_uc_pt.py` | `tests/expected_uc_pt.json` | Same. |
| `capture_parity_fixtures.py` | `tests/fixtures/parity/*.json` | Same. |

The three `capture_expected_*` / `capture_parity_*` scripts additionally refuse
if `klotho` resolved to this repository, because a baseline captured from the
code it is meant to check is not a baseline:

```bash
git worktree add .worktree-remote origin/main
KLOTHO_ALLOW_REGEN=1 PYTHONPATH=.worktree-remote python scripts/capture_expected_uc_pt.py \
    > tests/expected_uc_pt.json
```

Then commit the regenerated file **alone**, so its diff is reviewable in
isolation — and read that diff.

## Everything else

| Script | What it is |
|---|---|
| `benchmark_rt.py`, `benchmark_pt.py` | Timing harnesses for the RhythmTree and ParameterTree stacks. |
| `compare_benchmarks.py` | Diffs two benchmark runs. |
| `graphify_update.sh` | The **only** supported way to refresh `graphify-out/`. A bare `graphify update` has corrupted the graph before. |
| `migrate_examples_to_fluent.py` | One-time migration of example notebooks to the fluent selector API. Kept for provenance. |
| `snapshot_examples.py` | Dumps every `CompositionalUnit` and `Score` in the example notebooks. |
| `test_envelope_guardrails.py` | A **manual** harness despite the name. `pytest.ini` sets `testpaths = tests`, so it is never collected — do not assume it runs in CI. |

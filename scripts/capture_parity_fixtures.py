"""Capture parity fixtures from all scenarios.

Run ONCE against the unchanged pre-refactor codebase. Commits the resulting
JSON fixtures under ``tests/fixtures/parity/``. These freeze the current
behavior; after the UT/UC selector refactor, the parity test in
``tests/test_parity_refactor.py`` verifies the refactored code reproduces
the same fixtures byte-identically.

Do NOT regenerate these during the refactor. Fixture drift is a regression.
"""


import importlib.util
import json
import sys
from pathlib import Path



REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

SCENARIO_DIR = REPO_ROOT / "tests" / "fixtures" / "parity" / "scenarios"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "parity"

SCENARIOS = [
    "chronostasis",
    "entertain_me",
    "polyriddim",
    "score_demo_multi",
    "score_control_envs_3layer",
    "score_drones_voice1",
    "build_uc_helper",
]


def _load_scenario(name: str, filename: str | None = None):
    path = SCENARIO_DIR / (filename or f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"parity_scenario_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_capture_helper():
    path = FIXTURE_DIR / "capture.py"
    spec = importlib.util.spec_from_file_location("parity_capture", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    capture = _load_capture_helper()
    for name in SCENARIOS:
        mod = _load_scenario(name)
        result = mod.build()
        payload = capture.serialize(result, seed=mod.SEED, name=name)
        out_path = FIXTURE_DIR / f"{name}.json"
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        print(f"[capture] {name}: wrote {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    # --- oracle lock ---------------------------------------------------
    # Inside __main__ on purpose: tests/test_uc_pt_regression.py imports
    # this module for its serialisers, and a guard at import scope kills
    # the whole test run. Guard the ACT, not the file.
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / 'tests'))
    from _oracle_lock import require_regen_authorization as _require
    _require('tests/fixtures/parity/*.json', must_import_remote=True)
    # -------------------------------------------------------------------
    main()

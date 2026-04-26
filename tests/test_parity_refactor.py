"""Parity test: the refactored fluent API must reproduce the pre-refactor
golden-master fixtures byte-identically.

Fixtures under ``tests/fixtures/parity/*.json`` were captured from the
verbose pre-refactor API in an isolated commit. For each scenario, a
``<name>_refactored.py`` sibling script under
``tests/fixtures/parity/scenarios/`` uses the new fluent selector syntax
(``uc.root.set_pfields(...)``, ``uc.leaves.apply_envelope(...)``, etc.)
to produce the same composition.

The test loads the fixture and runs the refactored scenario, then asserts
deep equality of the serialized state. Any drift is a regression.

Note: scenarios are loaded via ``importlib.util.spec_from_file_location``
(NOT as a package) to keep ``tests/`` as a flat pytest layout without
``__init__.py`` files.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


TESTS_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = TESTS_DIR / "fixtures" / "parity"
SCENARIO_DIR = FIXTURE_DIR / "scenarios"


SCENARIOS = [
    "chronostasis",
    "entertain_me",
    "polyriddim",
    "score_demo_multi",
    "score_control_envs_3layer",
    "score_drones_voice1",
    "build_uc_helper",
]


def _load_module(path: Path, unique_name: str):
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def capture_helper():
    return _load_module(FIXTURE_DIR / "capture.py", "parity_capture_test")


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_refactor_preserves_behavior(scenario, capture_helper):
    fixture_path = FIXTURE_DIR / f"{scenario}.json"
    refactored_path = SCENARIO_DIR / f"{scenario}_refactored.py"

    with open(fixture_path) as f:
        expected = json.load(f)

    mod = _load_module(refactored_path, f"parity_refactored_{scenario}")
    np.random.seed(mod.SEED)
    result = mod.build()
    actual = capture_helper.serialize(result, seed=mod.SEED, name=scenario)

    # Round-trip through JSON to normalize any type differences between
    # fresh-captured and JSON-loaded (e.g. tuples vs lists).
    actual = json.loads(json.dumps(actual, sort_keys=True))

    assert actual == expected, (
        f"Parity break in scenario {scenario}. "
        f"The refactored fluent API does not reproduce the pre-refactor "
        f"byte-identical output."
    )

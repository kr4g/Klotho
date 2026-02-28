"""
Regression tests for UC/PT structure and events.

Compares current UC/PT output against baseline captured from remote (origin/main).
Run capture with: PYTHONPATH=.worktree-remote python scripts/capture_expected_uc_pt.py 2>/dev/null > tests/expected_uc_pt.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from klotho.chronos import TemporalUnitSequence as UTS, TemporalBlock as BT
from klotho.thetos import CompositionalUnit as UC, JsInstrument as JsInst
from klotho.tonos import Scale
from klotho.topos import Pattern

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "capture_uc_pt",
    project_root / "scripts" / "capture_expected_uc_pt.py",
)
_capture_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_capture_mod)
capture_uc = _capture_mod.capture_uc
_build_chronostasis_before = _capture_mod._build_chronostasis_before
_build_entertain_me_melody_before = _capture_mod._build_entertain_me_melody_before
_build_entertain_me_drums_before = _capture_mod._build_entertain_me_drums_before
_build_polyriddim_bass_before = _capture_mod._build_polyriddim_bass_before

EXPECTED_PATH = project_root / "tests" / "expected_uc_pt.json"
FLOAT_TOL = 1e-6


def _deep_compare(path, exp, act, float_tol=FLOAT_TOL):
    errs = []
    if type(exp) != type(act):
        errs.append(f"{path}: type mismatch {type(exp).__name__} vs {type(act).__name__}")
        return errs
    if isinstance(exp, dict):
        all_keys = set(exp.keys()) | set(act.keys())
        for k in all_keys:
            if k not in exp:
                errs.append(f"{path}.{k}: unexpected key in actual")
            elif k not in act:
                errs.append(f"{path}.{k}: missing in actual")
            else:
                errs.extend(_deep_compare(f"{path}.{k}", exp[k], act[k], float_tol))
    elif isinstance(exp, (list, tuple)):
        if len(exp) != len(act):
            errs.append(f"{path}: length mismatch {len(exp)} vs {len(act)}")
        for i, (e, a) in enumerate(zip(exp, act)):
            errs.extend(_deep_compare(f"{path}[{i}]", e, a, float_tol))
        if len(exp) != len(act):
            for i in range(min(len(exp), len(act)), max(len(exp), len(act))):
                side = "expected" if i < len(exp) else "actual"
                errs.append(f"{path}[{i}]: extra in {side}")
    elif isinstance(exp, (int, str, bool, type(None))):
        if exp != act:
            errs.append(f"{path}: {repr(exp)} != {repr(act)}")
    elif isinstance(exp, float):
        if act is None or not isinstance(act, (int, float)):
            errs.append(f"{path}: expected float, got {type(act).__name__}")
        elif abs(exp - act) > float_tol:
            errs.append(f"{path}: {exp} != {act} (diff {abs(exp-act)})")
    else:
        if exp != act:
            errs.append(f"{path}: {repr(exp)[:80]} != {repr(act)[:80]}")
    return errs


def _assert_captures_equal(name, expected, actual):
    errs = []
    for section in ("rt", "pt", "events"):
        if section not in expected:
            errs.append(f"{name}.{section}: missing in expected")
            continue
        if section not in actual:
            errs.append(f"{name}.{section}: missing in actual")
            continue
        errs.extend(_deep_compare(f"{name}.{section}", expected[section], actual[section]))
    if errs:
        pytest.fail("\n".join(errs[:50]) + ("\n... and more" if len(errs) > 50 else ""))


@pytest.fixture(scope="module")
def expected():
    with open(EXPECTED_PATH) as f:
        return json.load(f)


class TestUC_PT_RegressionChronostasis:
    def test_chronostasis_v0_u0(self, expected):
        np.random.seed(42)
        block = _build_chronostasis_before()
        rows = list(block)
        unit = rows[0][0]
        actual = capture_uc("chronostasis_v0_u0", unit)
        _assert_captures_equal("chronostasis_v0_u0", expected["uc"]["chronostasis_v0_u0"], actual)

    def test_chronostasis_v0_u1(self, expected):
        np.random.seed(42)
        block = _build_chronostasis_before()
        rows = list(block)
        unit = rows[0][1]
        actual = capture_uc("chronostasis_v0_u1", unit)
        _assert_captures_equal("chronostasis_v0_u1", expected["uc"]["chronostasis_v0_u1"], actual)

    def test_chronostasis_v1_u0(self, expected):
        np.random.seed(42)
        block = _build_chronostasis_before()
        rows = list(block)
        unit = rows[1][0]
        actual = capture_uc("chronostasis_v1_u0", unit)
        _assert_captures_equal("chronostasis_v1_u0", expected["uc"]["chronostasis_v1_u0"], actual)

    def test_chronostasis_v1_u1(self, expected):
        np.random.seed(42)
        block = _build_chronostasis_before()
        rows = list(block)
        unit = rows[1][1]
        actual = capture_uc("chronostasis_v1_u1", unit)
        _assert_captures_equal("chronostasis_v1_u1", expected["uc"]["chronostasis_v1_u1"], actual)


class TestUC_PT_RegressionEntertainMe:
    def test_entertain_me_melody(self, expected):
        uc = _build_entertain_me_melody_before()
        actual = capture_uc("entertain_me_melody", uc)
        _assert_captures_equal("entertain_me_melody", expected["uc"]["entertain_me_melody"], actual)

    def test_entertain_me_drums(self, expected):
        uc = _build_entertain_me_drums_before()
        actual = capture_uc("entertain_me_drums", uc)
        _assert_captures_equal("entertain_me_drums", expected["uc"]["entertain_me_drums"], actual)


class TestUC_PT_RegressionPolyriddim:
    def test_polyriddim_u0(self, expected):
        np.random.seed(42)
        uts3 = _build_polyriddim_bass_before()
        actual = capture_uc("polyriddim_u0", uts3[0])
        _assert_captures_equal("polyriddim_u0", expected["uc"]["polyriddim_u0"], actual)

    def test_polyriddim_u1(self, expected):
        np.random.seed(42)
        uts3 = _build_polyriddim_bass_before()
        actual = capture_uc("polyriddim_u1", uts3[1])
        _assert_captures_equal("polyriddim_u1", expected["uc"]["polyriddim_u1"], actual)


class TestUC_PT_RegressionDeterministic:
    def test_set_pfields_root(self, expected):
        uc = UC(tempus="4/4", prolatio=(1, 1, 1, 1), beat="1/4", bpm=120, inst=JsInst.Kalimba())
        uc.set_pfields(0, freq=440)
        actual = capture_uc("set_pfields_root", uc)
        _assert_captures_equal("set_pfields_root", expected["uc"]["set_pfields_root"], actual)

    def test_set_pfields_per_leaf(self, expected):
        uc = UC(tempus="4/4", prolatio=(1, 1, 1, 1), beat="1/4", bpm=120, inst=JsInst.Kalimba())
        freqs = [262, 330, 392, 523]
        for i, leaf in enumerate(uc.rt.leaf_nodes):
            uc.set_pfields(leaf, freq=freqs[i])
        actual = capture_uc("set_pfields_per_leaf", uc)
        _assert_captures_equal("set_pfields_per_leaf", expected["uc"]["set_pfields_per_leaf"], actual)

    def test_set_mfields_inheritance(self, expected):
        uc = UC(
            tempus="4/4",
            prolatio=((3, (1,) * 3), (2, (1,) * 2)),
            beat="1/4",
            bpm=120,
            inst=JsInst.Kalimba(),
        )
        limbs = uc.rt.at_depth(1)
        uc.set_mfields(limbs[0], idx=0, drct=1)
        uc.set_mfields(limbs[1], idx=5, drct=-1)
        actual = capture_uc("set_mfields_inheritance", uc)
        _assert_captures_equal(
            "set_mfields_inheritance",
            expected["uc"]["set_mfields_inheritance"],
            actual,
        )

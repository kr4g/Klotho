import importlib.util
import json
from pathlib import Path

import pytest

from klotho.chronos import TemporalUnitSequence as UTS
from klotho.utils.playback.supersonic.converters import convert_to_sc_events

_TESTS_DIR = Path(__file__).resolve().parent

_BUILD_SPEC = importlib.util.spec_from_file_location(
    "selector_api_parity_builders",
    _TESTS_DIR / "selector_api_parity_builders.py",
)
_BUILD = importlib.util.module_from_spec(_BUILD_SPEC)
_BUILD_SPEC.loader.exec_module(_BUILD)
build_rt_preview_chronostasis_fluent = _BUILD.build_rt_preview_chronostasis_fluent
build_rt_preview_chronostasis_legacy = _BUILD.build_rt_preview_chronostasis_legacy
build_rt_preview_entertain_fluent = _BUILD.build_rt_preview_entertain_fluent
build_rt_preview_entertain_legacy = _BUILD.build_rt_preview_entertain_legacy
build_rt_preview_poly_fluent = _BUILD.build_rt_preview_poly_fluent
build_rt_preview_poly_legacy = _BUILD.build_rt_preview_poly_legacy
build_uc_uts_helper_fluent = _BUILD.build_uc_uts_helper_fluent
build_uc_uts_helper_legacy = _BUILD.build_uc_uts_helper_legacy

_cap_spec = importlib.util.spec_from_file_location(
    "parity_capture_selector_api",
    _TESTS_DIR / "fixtures" / "parity" / "capture.py",
)
_cap_mod = importlib.util.module_from_spec(_cap_spec)
_cap_spec.loader.exec_module(_cap_mod)


def _canonical_sc_events(obj):
    id_norm = _cap_mod._IdNormalizer()
    ev = convert_to_sc_events(obj)
    return json.loads(json.dumps(_cap_mod._canonicalize(ev, id_norm), sort_keys=True))


def _canonical_tone_payload(obj):
    from klotho.utils.playback.tonejs.converters import convert_to_events

    id_norm = _cap_mod._IdNormalizer()
    payload = convert_to_events(obj)
    return json.loads(json.dumps(_cap_mod._canonicalize(payload, id_norm), sort_keys=True))


@pytest.mark.parametrize(
    "legacy_fn, fluent_fn",
    [
        (build_rt_preview_chronostasis_legacy, build_rt_preview_chronostasis_fluent),
        (build_rt_preview_entertain_legacy, build_rt_preview_entertain_fluent),
        (build_rt_preview_poly_legacy, build_rt_preview_poly_fluent),
    ],
)
def test_rt_preview_legacy_vs_fluent_tone_payload(legacy_fn, fluent_fn):
    a = _canonical_tone_payload(legacy_fn())
    b = _canonical_tone_payload(fluent_fn())
    assert a == b


def test_uc_uts_supersonic_helper_legacy_vs_fluent():
    cmaj = (261.63, 329.63, 392.0)
    amin = (220.0, 261.63, 329.63)
    fmaj = (174.61, 220.0, 261.63)
    gmaj = (196.0, 246.94, 293.66)

    a = build_uc_uts_helper_legacy(
        "4/4",
        (1, 1, 1, 1),
        [cmaj, amin, fmaj, gmaj],
        rests=[2],
        slur_spans=[(0, 2)],
        strum_values=[0.2, -0.4, 0.0, 0.7],
    )
    b = build_uc_uts_helper_fluent(
        "4/4",
        (1, 1, 1, 1),
        [cmaj, amin, fmaj, gmaj],
        rests=[2],
        slur_spans=[(0, 2)],
        strum_values=[0.2, -0.4, 0.0, 0.7],
    )
    assert _canonical_sc_events(a) == _canonical_sc_events(b)

    u1 = UTS(
        [
            build_uc_uts_helper_legacy(
                "4/4",
                (1, 1, 1, 1),
                [cmaj, amin, fmaj, gmaj],
                rests=[2],
            ),
            build_uc_uts_helper_legacy(
                "5/8",
                (2, 1, 1, 1),
                [fmaj, gmaj, cmaj, amin],
                rests=[0],
            ),
        ]
    )
    u2 = UTS(
        [
            build_uc_uts_helper_fluent(
                "4/4",
                (1, 1, 1, 1),
                [cmaj, amin, fmaj, gmaj],
                rests=[2],
            ),
            build_uc_uts_helper_fluent(
                "5/8",
                (2, 1, 1, 1),
                [fmaj, gmaj, cmaj, amin],
                rests=[0],
            ),
        ]
    )
    assert _canonical_sc_events(u1) == _canonical_sc_events(u2)

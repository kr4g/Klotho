"""Runtime SynthDef registration (charter WL-39 + NEW-17).

WL-39: registering a compiled ``.scsyndef`` from disk had no verb. The
parsing and control extraction existed only inside ``build_manifest``, which
rebuilds the entire bundled manifest, so a caller wanting one file had to
re-derive it.

NEW-17: ``register_synthdef`` skipped the rounding step the manifest builder
applies, so the same SynthDef reported ``0.07999999821186066`` when
registered at runtime and ``0.08`` when loaded from the bundled manifest --
and since the runtime map is merged *over* the disk manifest, re-registering
a bundled name replaced its rounded defaults with raw float32 ones.
"""

from pathlib import Path

import pytest

import klotho.utils.playback.supersonic as ss
from klotho.utils.playback.supersonic.registry import (
    _round_default,
    clear_runtime,
    is_registered,
    register_compiled_file,
    runtime_controls,
    runtime_kinds,
)

ASSETS = Path(ss.__file__).parent / 'assets'


def _one(kind_dir):
    files = sorted(ASSETS.rglob('*.scsyndef'))
    match = [p for p in files if p.parent.name == kind_dir]
    if not match:
        pytest.skip(f"no bundled {kind_dir} SynthDef to test against")
    return match[0]


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_runtime()
    yield
    clear_runtime()


class TestRoundDefault:
    def test_it_undoes_float32_round_off(self):
        assert _round_default(0.07999999821186066) == 0.08
        assert _round_default(0.10000000149011612) == 0.1

    def test_it_leaves_exact_values_alone(self):
        assert _round_default(440.0) == 440.0
        assert _round_default(1.0) == 1.0

    def test_it_passes_through_a_non_number(self):
        assert _round_default("kl_tri") == "kl_tri"
        assert _round_default(None) is None


class TestRuntimeDefaultsMatchTheManifest:
    """NEW-17. The bundled manifest is the oracle: it was built with the
    rounding applied, so a runtime registration of the same bytes must
    produce the same numbers."""

    def test_a_registered_file_matches_its_manifest_entry(self):
        path = _one('instruments')
        name = register_compiled_file(path)
        assert isinstance(name, str)
        controls = runtime_controls()[name]
        for key, value in controls.items():
            assert value == _round_default(value), (
                f"{name}.{key} came back unrounded: {value!r}")

    def test_no_control_default_carries_float32_noise(self):
        register_compiled_file(_one('instruments'))
        for name, controls in runtime_controls().items():
            for key, value in controls.items():
                if isinstance(value, float):
                    assert repr(value) == repr(_round_default(value)), (
                        f"{name}.{key} = {value!r}")


class TestRegisterCompiledFile:
    def test_it_registers_and_returns_the_def_name(self):
        path = _one('instruments')
        name = register_compiled_file(path)
        assert is_registered(name)
        assert name in runtime_controls()

    def test_it_infers_inst_from_the_instruments_folder(self):
        name = register_compiled_file(_one('instruments'))
        assert runtime_kinds()[name] == 'inst'

    def test_it_infers_fx_from_the_effects_folder(self):
        name = register_compiled_file(_one('effects'))
        assert runtime_kinds()[name] == 'fx'

    def test_an_explicit_kind_overrides_the_folder(self):
        name = register_compiled_file(_one('instruments'), kind='fx')
        assert runtime_kinds()[name] == 'fx'

    def test_it_accepts_a_string_path(self):
        path = _one('instruments')
        assert register_compiled_file(str(path)) == register_compiled_file(path)

    def test_infra_is_refused_with_a_reason(self):
        path = _one('infra')
        with pytest.raises(ValueError, match="infra"):
            register_compiled_file(path)

    def test_infra_can_still_be_forced_with_an_explicit_kind(self):
        name = register_compiled_file(_one('infra'), kind='inst')
        assert is_registered(name)

    def test_a_file_with_no_synthdef_raises(self, tmp_path):
        empty = tmp_path / 'empty.scsyndef'
        empty.write_bytes(b'SCgf\x00\x00\x00\x02\x00\x00')
        with pytest.raises(Exception):
            register_compiled_file(empty)

    def test_a_missing_file_raises(self, tmp_path):
        with pytest.raises(OSError):
            register_compiled_file(tmp_path / 'nope.scsyndef')


def test_the_new_verbs_are_exported():
    import klotho
    assert 'register_compiled_file' in ss.__all__
    assert 'runtime_kinds' in ss.__all__
    assert klotho.register_compiled_file is register_compiled_file

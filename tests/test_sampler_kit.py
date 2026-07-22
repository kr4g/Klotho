"""Tests for the bundled sample-player instruments (`kl_sampler1`/`kl_sampler2`),
the beatbox SynthDefKit, integer-index Kit member access, tuple selector
polyphony, symbolic `buf` pfields through validation/lowering, and sample
collection in the SuperSonic engine."""

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.base import Kit, Instrument
from klotho.thetos.instruments.synthdef import SynthDefInstrument, SynthDefKit
from klotho.utils.playback._sc_validate import (
    AssemblyValidationError, validate_sc_events,
)
from klotho.utils.playback._sc_assembly import (
    lower_compositional_ir_to_sc_assembly,
)
from klotho.utils.playback.supersonic.converters import (
    convert_score_to_sc_events,
)
from klotho.utils.playback.supersonic.samples import (
    load_sample_manifest, sample_names, sample_info, sample_groups,
)

BB_ORDER = [
    'bb_kick', 'bb_hihat', 'bb_snare', 'bb_shake',
    'bb_big_kick', 'bb_voice', 'bb_snare2', 'bb_openhihat',
]

TABLA_ORDER = [
    'tabla1', 'tabla2', 'tabla3', 'tabla4',
    'tabla_tas1', 'tabla_tas2', 'tabla_tas3',
    'tabla_te1', 'tabla_te2', 'tabla_te_m', 'tabla_te_ne',
    'tabla_tun1', 'tabla_tun2', 'tabla_tun3',
]


def _beatbox():
    return SynthDefKit.beatbox()


def _uc(**kwargs):
    defaults = dict(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60)
    defaults.update(kwargs)
    return UC(**defaults)


def _new_events(events):
    return [e for e in events if e.get('type') == 'new' and e.get('defName') != '__rest__']


class TestSampleManifest:
    def test_manifest_has_all_beatbox_samples_in_order(self):
        assert sample_names('beatbox') == BB_ORDER

    def test_manifest_has_all_tabla_samples_in_order(self):
        assert sample_names('tabla') == TABLA_ORDER

    def test_groups(self):
        assert sample_groups() == ['beatbox', 'tabla']

    def test_duplicate_snare_disambiguated(self):
        manifest = load_sample_manifest()
        assert manifest['bb_snare']['file'] == 'beatbox/2_bb_snare.wav'
        assert manifest['bb_snare2']['file'] == 'beatbox/6_bb_snare.wav'

    def test_duplicate_tablas_numbered(self):
        manifest = load_sample_manifest()
        assert manifest['tabla1']['file'] == 'tabla/0_tabla.wav'
        assert manifest['tabla4']['file'] == 'tabla/3_tabla.wav'

    def test_files_resolve_on_disk(self):
        from klotho.utils.playback.supersonic.samples import SAMPLES_DIR
        for info in load_sample_manifest().values():
            assert (SAMPLES_DIR / info['file']).exists(), info['file']

    def test_sample_info_unknown_name_raises(self):
        with pytest.raises(KeyError, match='Unknown sample'):
            sample_info('nope')

    def test_entries_have_metadata(self):
        info = sample_info('bb_kick')
        assert info['channels'] == 2
        assert info['sampleRate'] == 44100
        assert info['frames'] > 0
        assert info['duration'] > 0
        assert info['group'] == 'beatbox'


class TestSamplerInstrument:
    def test_defname_follows_channel_count(self):
        inst = SynthDefInstrument.sampler('bb_kick')
        assert inst.defName == 'kl_sampler2'

    def test_buf_is_symbolic_name(self):
        inst = SynthDefInstrument.sampler('bb_snare')
        assert inst.pfields['buf'] == 'bb_snare'

    def test_default_is_one_shot_with_duration(self):
        inst = SynthDefInstrument.sampler('bb_kick')
        assert not inst.has_gate
        assert 'duration' in inst.pfields

    def test_duration_none_drops_pfield(self):
        inst = SynthDefInstrument.sampler('bb_kick', duration=None)
        assert 'duration' not in inst.pfields

    def test_overrides_applied(self):
        inst = SynthDefInstrument.sampler('bb_kick', rate=-1.0, pos=1.0, amp=0.8)
        assert inst.pfields['rate'] == -1.0
        assert inst.pfields['pos'] == 1.0
        assert inst.pfields['amp'] == 0.8

    def test_unknown_sample_raises(self):
        with pytest.raises(KeyError):
            SynthDefInstrument.sampler('bb_nonexistent')


class TestKitIndexAccess:
    def test_index_zero_is_default(self):
        kit = _beatbox()
        assert kit._resolve(0) is kit.members['bb_kick']
        assert kit._resolve(0) is kit._resolve(None)

    def test_index_order_matches_member_order(self):
        kit = _beatbox()
        for i, key in enumerate(BB_ORDER):
            assert kit._resolve(i) is kit.members[key]

    def test_index_wraps_mod_len(self):
        kit = _beatbox()
        assert kit._resolve(9) is kit._resolve(1)
        assert kit._resolve(-1) is kit._resolve(7)

    def test_getitem_by_index(self):
        kit = _beatbox()
        assert kit[3] is kit.members['bb_shake']
        assert kit[11] is kit.members['bb_shake']

    def test_string_keys_still_work(self):
        kit = _beatbox()
        assert kit['bb_voice'] is kit.members['bb_voice']
        assert kit._resolve('bb_voice') is kit.members['bb_voice']

    def test_unknown_key_raises(self):
        kit = _beatbox()
        with pytest.raises(KeyError, match="Unknown voice 'not_a_member'"):
            kit._resolve('not_a_member')

    def test_bool_is_not_an_index(self):
        members = {'a': Instrument('a', {'x': 1}), 'b': Instrument('b', {'x': 2})}
        kit = Kit(members)
        assert kit._resolve(True) is kit.members['a']


class TestBeatboxKit:
    def test_member_keys_and_order(self):
        kit = _beatbox()
        assert list(kit.members.keys()) == BB_ORDER

    def test_default_and_selector(self):
        kit = _beatbox()
        assert kit.default == 'bb_kick'
        assert kit.selector == 'voice'

    def test_all_members_are_stereo_samplers(self):
        kit = _beatbox()
        for key, member in kit.members.items():
            assert member.defName == 'kl_sampler2'
            assert member.pfields['buf'] == key if key != 'bb_snare2' else True

    def test_overrides_reach_every_member(self):
        kit = SynthDefKit.beatbox(amp=0.25)
        assert all(m.pfields['amp'] == 0.25 for m in kit.members.values())

    def test_from_samples_with_mapping(self):
        kit = SynthDefKit.from_samples({'k': 'bb_kick', 's': 'bb_snare'})
        assert list(kit.members.keys()) == ['k', 's']
        assert kit.members['s'].pfields['buf'] == 'bb_snare'


class TestTablaKit:
    def test_member_keys_and_order(self):
        kit = SynthDefKit.tabla()
        assert list(kit.members.keys()) == TABLA_ORDER
        assert kit.default == 'tabla1'

    def test_mono_and_stereo_members_pick_correct_def(self):
        kit = SynthDefKit.tabla()
        assert kit['tabla1'].defName == 'kl_sampler2'      # stereo
        assert kit['tabla_tas1'].defName == 'kl_sampler1'  # mono

    def test_index_wraps_mod_14(self):
        kit = SynthDefKit.tabla()
        assert kit[14] is kit['tabla1']
        assert kit[17] is kit['tabla4']

    def test_unknown_group_raises(self):
        with pytest.raises(KeyError, match='Unknown sample group'):
            SynthDefKit.from_sample_group('bongos')

    def test_lowering_resolves_mixed_channel_members(self):
        uc = _uc(inst=SynthDefKit.tabla())
        uc.leaves.set_pfields(voice=('tabla1', 'tabla_te1'))
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        defs = {e['pfields']['buf']: e['defName'] for e in news}
        assert defs['tabla1'] == 'kl_sampler2'
        assert defs['tabla_te1'] == 'kl_sampler1'


class TestValidatorBufStrings:
    def _event(self, pfields):
        return [{
            'type': 'new', 'id': 'x', 'defName': 'kl_sampler2',
            'start': 0.0, 'dur': 1.0, 'pfields': pfields,
        }]

    def test_buf_string_accepted(self):
        validate_sc_events(self._event({'buf': 'bb_kick', 'amp': 0.5}))

    def test_empty_buf_string_rejected(self):
        with pytest.raises(AssemblyValidationError):
            validate_sc_events(self._event({'buf': ''}))

    def test_non_buf_string_still_rejected(self):
        with pytest.raises(AssemblyValidationError):
            validate_sc_events(self._event({'freq': 'oops'}))


class TestUCLowering:
    def test_kit_events_resolve_member_defname_and_buf(self):
        uc = _uc(inst=_beatbox(), pfields=['voice'])
        uc.set_pfields(uc.root, voice='bb_snare')
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        assert len(news) == 4
        for ev in news:
            assert ev['defName'] == 'kl_sampler2'
            assert ev['pfields']['buf'] == 'bb_snare'
            assert 'voice' not in ev['pfields']

    def test_duration_injected_from_leaf(self):
        uc = _uc(inst=_beatbox())
        events = lower_compositional_ir_to_sc_assembly(uc)
        for ev in _new_events(events):
            assert ev['pfields']['duration'] == pytest.approx(1.0)
            assert ev['releaseAfter'] is True

    def test_integer_index_selector(self):
        uc = _uc(inst=_beatbox(), pfields=['voice'])
        uc.set_pfields(uc.root, voice=2)
        events = lower_compositional_ir_to_sc_assembly(uc)
        for ev in _new_events(events):
            assert ev['pfields']['buf'] == 'bb_snare'

    def test_events_pass_validation(self):
        uc = _uc(inst=_beatbox(), pfields=['voice'])
        uc.set_pfields(uc.root, voice='bb_hihat')
        events = lower_compositional_ir_to_sc_assembly(uc)
        validate_sc_events(events)


class TestTupleSelectorPolyphony:
    def test_tuple_of_keys_yields_per_voice_bufs(self):
        uc = _uc(inst=_beatbox(), pfields=['voice'])
        uc.set_pfields(uc.root, voice=('bb_kick', 'bb_hihat'))
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        assert len(news) == 8
        by_step = {}
        for ev in news:
            by_step.setdefault(ev['_logicalStepId'], []).append(ev)
        for step_events in by_step.values():
            bufs = sorted(e['pfields']['buf'] for e in step_events)
            assert bufs == ['bb_hihat', 'bb_kick']

    def test_tuple_of_indices(self):
        uc = _uc(inst=_beatbox(), pfields=['voice'])
        uc.set_pfields(uc.root, voice=(0, 3, 7))
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        assert len(news) == 12
        step = {}
        for ev in news:
            step.setdefault(ev['_logicalStepId'], []).append(ev['pfields']['buf'])
        for bufs in step.values():
            assert sorted(bufs) == sorted(['bb_kick', 'bb_shake', 'bb_openhihat'])

    def test_mixed_key_and_index_tuple(self):
        uc = _uc(inst=_beatbox(), pfields=['voice'])
        uc.set_pfields(uc.root, voice=('bb_voice', 1))
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        bufs = {e['pfields']['buf'] for e in news}
        assert bufs == {'bb_voice', 'bb_hihat'}

    def test_shorter_companion_tuple_mod_cycles(self):
        uc = _uc(inst=_beatbox(), pfields=['voice', 'rate'])
        uc.set_pfields(uc.root, voice=(0, 1, 2), rate=(1.0, 2.0))
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        step = {}
        for ev in news:
            step.setdefault(ev['_logicalStepId'], []).append(ev)
        for step_events in step.values():
            assert len(step_events) == 3
            pairs = {(e['pfields']['buf'], e['pfields']['rate']) for e in step_events}
            assert pairs == {
                ('bb_kick', 1.0), ('bb_hihat', 2.0), ('bb_snare', 1.0),
            }

    def test_mixed_gating_kit_per_voice(self):
        kit = SynthDefKit(
            {
                'samp': SynthDefInstrument.sampler('bb_kick'),
                'tri': SynthDefInstrument.tri(),
            },
        )
        uc = _uc(inst=kit, pfields=['voice'])
        uc.set_pfields(uc.root, voice=('samp', 'tri'))
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        def_names = {e['defName'] for e in news}
        assert def_names == {'kl_sampler2', 'kl_tri'}
        for ev in news:
            if ev['defName'] == 'kl_sampler2':
                assert 'duration' in ev['pfields']
                assert 'gate' not in ev['pfields']

    def test_tuple_events_pass_validation(self):
        uc = _uc(inst=_beatbox(), pfields=['voice'])
        uc.set_pfields(uc.root, voice=('bb_kick', 'bb_snare2'))
        events = lower_compositional_ir_to_sc_assembly(uc)
        validate_sc_events(events)


class TestScoreNewKit:
    def test_kit_member_resolved_from_selector(self):
        s = Score()
        s.new(start=0.0, dur=0.5, inst=_beatbox(), voice='bb_openhihat')
        payload = convert_score_to_sc_events(s)
        news = _new_events(payload['events'])
        assert len(news) == 1
        assert news[0]['defName'] == 'kl_sampler2'
        assert news[0]['pfields']['buf'] == 'bb_openhihat'
        assert 'voice' not in news[0]['pfields']

    def test_default_member_when_selector_absent(self):
        s = Score()
        s.new(start=0.0, dur=0.5, inst=_beatbox())
        payload = convert_score_to_sc_events(s)
        news = _new_events(payload['events'])
        assert news[0]['pfields']['buf'] == 'bb_kick'

    def test_tuple_selector_expands_to_voices(self):
        s = Score()
        s.new(start=0.0, dur=0.5, inst=_beatbox(), voice=('bb_kick', 4))
        payload = convert_score_to_sc_events(s)
        news = _new_events(payload['events'])
        assert len(news) == 2
        assert {e['pfields']['buf'] for e in news} == {'bb_kick', 'bb_big_kick'}

    def test_explicit_duration_overrides_injection(self):
        s = Score()
        s.new(start=0.0, dur=2.0, inst=_beatbox(), duration=0.25)
        payload = convert_score_to_sc_events(s)
        news = _new_events(payload['events'])
        assert news[0]['pfields']['duration'] == 0.25

    def test_injected_duration_tracks_dur(self):
        s = Score()
        s.new(start=0.0, dur=1.5, inst=_beatbox())
        payload = convert_score_to_sc_events(s)
        news = _new_events(payload['events'])
        assert news[0]['pfields']['duration'] == pytest.approx(1.5)


class TestEngineSampleCollection:
    def _engine(self, events):
        from klotho.utils.playback.supersonic.engine import SuperSonicEngine
        return SuperSonicEngine(events)

    def _event(self, buf, defname='kl_sampler2'):
        return {
            'type': 'new', 'id': f'e_{buf}', 'defName': defname,
            'start': 0.0, 'dur': 1.0, 'pfields': {'buf': buf, 'amp': 0.5},
        }

    def test_collects_only_referenced_samples(self):
        engine = self._engine([self._event('bb_kick'), self._event('bb_voice')])
        assert set(engine.sample_assets.keys()) == {'bb_kick', 'bb_voice'}
        for asset in engine.sample_assets.values():
            assert asset['b64']
            assert asset['channels'] == 2

    def test_no_samples_no_assets(self):
        events = [{
            'type': 'new', 'id': 'x', 'defName': 'kl_tri',
            'start': 0.0, 'dur': 1.0, 'pfields': {'freq': 440.0, 'gate': 1},
        }]
        engine = self._engine(events)
        assert engine.sample_assets == {}

    def test_unknown_sample_name_raises(self):
        with pytest.raises(KeyError, match='Unknown sample'):
            self._engine([self._event('bb_nope')])

    def test_sampler_synthdef_asset_included(self):
        engine = self._engine([self._event('bb_kick')])
        assert 'kl_sampler2' in engine.synthdef_assets

    def test_widget_html_embeds_samples(self):
        engine = self._engine([self._event('bb_kick')])
        html = engine._generate_html()
        assert 'bb_kick' in html
        assert '__SAMPLES_JSON__' not in html


class TestManifestEntries:
    def test_sampler_defs_in_manifest(self):
        from klotho.thetos.instruments._shared import (
            ss_synth_controls, ss_synth_kind,
        )
        for name in ('kl_sampler1', 'kl_sampler2'):
            controls = ss_synth_controls(name)
            assert 'gate' not in controls
            for key in ('buf', 'rate', 'pos', 'loop', 'duration',
                        'attackTime', 'releaseTime', 'amp', 'pan'):
                assert key in controls, f'{name} missing {key}'
            assert ss_synth_kind(name) == 'inst'

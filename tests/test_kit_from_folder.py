"""SynthDefKit.from_folder and family round-robin selectors."""
import io
import wave
from pathlib import Path

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.synthdef import SynthDefInstrument, SynthDefKit
from klotho.thetos.instruments.ensemble import Ensemble
from klotho.utils.playback.supersonic.samples import clear_runtime_samples
from klotho.utils.playback.supersonic.converters import (
    convert_to_sc_events, convert_score_to_sc_events,
    convert_score_to_sc_animation_events,
)

DEMO_KIT_DIR = (Path(__file__).parent.parent / "examples"
                / "mat111mc_notebooks" / "mat_kit")


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_runtime_samples()
    yield
    clear_runtime_samples()


def make_wav(channels=1, seed=0, frames=500):
    bio = io.BytesIO()
    with wave.open(bio, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(bytes([seed % 256]) * (frames * channels * 2))
    return bio.getvalue()


@pytest.fixture
def kit_folder(tmp_path):
    root = tmp_path / 'my_kit'
    (root / 'snare').mkdir(parents=True)
    (root / 'sfx').mkdir()
    (root / 'kick').mkdir()
    (root / 'clap.wav').write_bytes(make_wav(seed=1))
    (root / 'snare' / '0_snare_a.wav').write_bytes(make_wav(seed=2))
    (root / 'snare' / '1_snare_b.wav').write_bytes(make_wav(seed=3))
    (root / 'snare' / '2_snare_c.wav').write_bytes(make_wav(seed=4))
    (root / 'sfx' / 'riser.wav').write_bytes(make_wav(seed=5))
    (root / 'sfx' / 'vinyl.wav').write_bytes(make_wav(seed=6))
    (root / 'kick' / 'kick.wav').write_bytes(make_wav(seed=7))
    return root


def bufs_of(events):
    return [ev['pfields'].get('buf') for ev in events
            if ev.get('type') == 'new'
            and str(ev.get('defName', '')).startswith('kl_sampler')]


class TestFromFolder:
    def test_structure(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        assert list(kit.members) == ['clap', 'kick', 'riser', 'vinyl',
                                     'snare_a', 'snare_b', 'snare_c']
        assert kit.families == ['sfx', 'snare']
        assert kit._families['snare'] == ['snare_a', 'snare_b', 'snare_c']
        # loose file is the first member -> default
        assert kit.default == 'clap'
        # samples registered kit-prefixed
        assert kit.members['clap'].pfields['buf'] == 'my_kit_clap'
        assert kit.members['snare_b'].pfields['buf'] == 'my_kit_snare_b'

    def test_single_file_family_dir_is_plain_member(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        # kick/kick.wav -> member 'kick', no one-member 'kick' family
        assert 'kick' in kit.members
        assert 'kick' not in kit.families

    def test_default_and_overrides(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder, default='kick', amp=0.9)
        assert kit.default == 'kick'
        assert kit.members['snare_a'].pfields['amp'] == 0.9
        with pytest.raises(KeyError, match='not a member'):
            SynthDefKit.from_folder(kit_folder, default='nope')

    def test_flat_folder_has_no_families(self, tmp_path):
        root = tmp_path / 'flat'
        root.mkdir()
        (root / 'a.wav').write_bytes(make_wav(seed=1))
        (root / 'b.wav').write_bytes(make_wav(seed=2))
        kit = SynthDefKit.from_folder(root)
        assert list(kit.members) == ['a', 'b']
        assert kit.families == []

    def test_empty_folder_errors(self, tmp_path):
        root = tmp_path / 'empty'
        root.mkdir()
        with pytest.raises(ValueError, match='No .wav files'):
            SynthDefKit.from_folder(root)

    def test_missing_folder_errors(self, tmp_path):
        with pytest.raises(NotADirectoryError):
            SynthDefKit.from_folder(tmp_path / 'nope')

    def test_duplicate_member_errors(self, tmp_path):
        root = tmp_path / 'dup'
        (root / 'fam').mkdir(parents=True)
        (root / 'hit.wav').write_bytes(make_wav(seed=1))
        (root / 'fam' / '0_hit.wav').write_bytes(make_wav(seed=2))
        with pytest.raises(ValueError, match="Duplicate kit member"):
            SynthDefKit.from_folder(root)

    def test_member_named_like_family_errors(self, tmp_path):
        root = tmp_path / 'clash'
        (root / 'snare').mkdir(parents=True)
        (root / 'snare' / 'snare.wav').write_bytes(make_wav(seed=1))
        (root / 'snare' / 'snare_alt.wav').write_bytes(make_wav(seed=2))
        with pytest.raises(ValueError, match='family folder'):
            SynthDefKit.from_folder(root)

    def test_demo_kit_fixture(self):
        """The demo kit doubles as a convention fixture (examples/ is
        untracked, so skip on checkouts without it)."""
        if not DEMO_KIT_DIR.is_dir():
            pytest.skip("demo kit assets not present in this checkout")
        kit = SynthDefKit.from_folder(DEMO_KIT_DIR)
        assert set(kit.families) == {'kick', 'snare', 'hat', 'clap',
                                     'wood', 'metal'}
        for loose in ('openhat', 'cowbell', 'snap'):
            assert loose in kit.members
        assert kit._families['snare'] == ['snare_a', 'snare_b',
                                          'snare_c', 'snare_d']


class TestFamilyRoundRobinUC:
    def test_scalar_family_rotates_per_leaf(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        uc = UC(tempus='4/4', prolatio=(1,) * 6, beat='1/4', bpm=120, inst=kit)
        uc.leaves.set_pfields(voice='snare')
        bufs = bufs_of(convert_to_sc_events(uc))
        assert bufs == ['my_kit_snare_a', 'my_kit_snare_b', 'my_kit_snare_c',
                        'my_kit_snare_a', 'my_kit_snare_b', 'my_kit_snare_c']

    def test_replay_is_identical(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        uc = UC(tempus='4/4', prolatio=(1,) * 5, beat='1/4', bpm=120, inst=kit)
        uc.leaves.set_pfields(voice='snare')
        first = bufs_of(convert_to_sc_events(uc))
        assert bufs_of(convert_to_sc_events(uc)) == first

    def test_display_matches_playback(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        uc = UC(tempus='4/4', prolatio=(1,) * 3, beat='1/4', bpm=120, inst=kit)
        uc.leaves.set_pfields(voice='snare')
        leaves = [ev for ev in uc if not ev.is_rest]
        shown = [lv.pfields['voice'] for lv in leaves]
        assert shown == ['snare_a', 'snare_b', 'snare_c']
        # repeated display access never perturbs lowering
        for lv in leaves:
            _ = lv.pfields
            _ = lv.pfields
        assert bufs_of(convert_to_sc_events(uc))[:3] == [
            'my_kit_snare_a', 'my_kit_snare_b', 'my_kit_snare_c']

    def test_tuple_selector_family_elements(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120, inst=kit)
        uc.leaves.set_pfields(voice=('snare', 'snare'))
        bufs = bufs_of(convert_to_sc_events(uc))
        # leaf 0 -> ordinals 0,1 ; leaf 1 -> ordinals 1,2
        assert bufs == ['my_kit_snare_a', 'my_kit_snare_b',
                        'my_kit_snare_b', 'my_kit_snare_c']

    def test_direct_member_selection_untouched(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        uc = UC(tempus='4/4', prolatio=(1,) * 4, beat='1/4', bpm=120, inst=kit)
        uc.leaves.set_pfields(voice='snare_b')
        bufs = bufs_of(convert_to_sc_events(uc))
        assert bufs == ['my_kit_snare_b'] * 4


class TestFamilyRoundRobinScoreEvents:
    def test_loose_events_rotate_and_reset(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        s = Score()
        for i in range(4):
            s.new(start=i * 0.5, dur=0.25, inst=kit, voice='snare', amp=0.5)
        expected = ['my_kit_snare_a', 'my_kit_snare_b', 'my_kit_snare_c',
                    'my_kit_snare_a']
        p1 = convert_score_to_sc_events(s)
        assert bufs_of(p1['events']) == expected
        # reset per conversion -> identical replay
        p2 = convert_score_to_sc_events(s)
        assert bufs_of(p2['events']) == expected

    def test_play_and_plot_payloads_agree(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        s = Score()
        for i in range(3):
            s.new(start=i * 0.5, dur=0.25, inst=kit, voice='snare', amp=0.5)
        p = convert_score_to_sc_events(s)
        a = convert_score_to_sc_animation_events(s)
        assert bufs_of(p['events']) == bufs_of(a['events'])

    def test_score_embedded_uc_rotates(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        uc = UC(tempus='4/4', prolatio=(1,) * 4, beat='1/4', bpm=120, inst=kit)
        uc.leaves.set_pfields(voice='snare')
        s = Score()
        s.track('drums')
        s.add(uc, name='groove', track='drums')
        bufs = bufs_of(convert_score_to_sc_events(s)['events'])
        assert bufs == ['my_kit_snare_a', 'my_kit_snare_b',
                        'my_kit_snare_c', 'my_kit_snare_a']


class TestKitSelectorAPI:
    def test_unknown_selector_lists_families(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        with pytest.raises(KeyError, match='families'):
            kit._resolve('not_a_thing')

    def test_pick_and_cycle_unchanged(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        assert kit.pick('snare') in ('snare_a', 'snare_b', 'snare_c')
        cyc = kit.cycle('snare')
        assert [next(cyc) for _ in range(4)] == [
            'snare_a', 'snare_b', 'snare_c', 'snare_a']

    def test_peek_does_not_advance(self, kit_folder):
        kit = SynthDefKit.from_folder(kit_folder)
        a = kit._resolve('snare', advance=False)
        b = kit._resolve('snare', advance=False)
        assert a is b  # peeking twice yields the same member

    def test_ensemble_family_call_form(self):
        """CONVENTIONS.md documents ens.family('drums') as always working."""
        ens = Ensemble('t')
        ens.add('k', SynthDefInstrument.sampler('bb_kick'), family='drums')
        assert ens.family('drums')['k'] is not None
        assert ens.family['drums']['k'] is not None

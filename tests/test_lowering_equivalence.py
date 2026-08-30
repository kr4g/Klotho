"""Full-pipeline lowering-equivalence oracle.

Builds a deterministic miniature score that exercises the surfaces the
performance work touches — rests, ties, slurs, poly/tuple pfields, kits,
control envelopes, nested UTS/BT alignment on all three axes, negative
score times, parent-level parameter inheritance, insert FX, and loose
Events — lowers it, and checks:

1. the payload matches a checked-in golden fixture (uuid-normalized), so
   any behavioral drift in build/copy/lowering fails a test instead of
   reaching students' installs;
2. the structural-clone fast copy and the legacy ``_copy_rebuild`` path
   produce byte-identical payloads;
3. every payload id (events + ``meta.inserts[*].uid``) is unique;
4. copies do not alias their originals (mutations in either direction
   stay private), and parent-level ``set()`` propagation keeps working
   on copies (override *placement* is preserved, not flattened).

PROVENANCE OF THE GOLDEN -- read before regenerating it.

This is a CHARACTERIZATION oracle, not a correctness oracle. Its values were
captured from this package's own output at a moment when that output was
believed correct, and its job is to detect DRIFT: it answers "did behaviour
change", never "is behaviour right". Nothing in it is derived from an external
reference, so it cannot testify that the pipeline is correct -- only that it
still does what it did.

That makes regeneration the one move that destroys it. A golden regenerated
from the working tree pins the code to itself and will then pass for any
behaviour, including the behaviour it was written to catch.

    python tests/test_lowering_equivalence.py --regen

Regenerate ONLY when a behaviour change was intended, and then:
  - eyeball and review the fixture diff line by line before committing it,
    with the intended change in hand -- every altered line must be one you
    can explain;
  - commit the regenerated golden ALONE, never in the same commit as the
    source change it pins, so the diff stays reviewable in isolation.

If a red run here was not expected, the golden is doing its job. Fix the code.
"""
import json
import re
from pathlib import Path

import pytest

from klotho.chronos import TemporalUnit as UT
from klotho.chronos import TemporalUnitSequence as UTS
from klotho.chronos import TemporalBlock as BT
from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.events import Event
from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.base import Kit
from klotho.thetos.instruments.synthdef import SynthDefInstrument, SynthDefFX
from klotho.utils.playback.supersonic.converters import convert_score_to_sc_events

GOLDEN_PATH = Path(__file__).parent / 'fixtures' / 'lowering_equivalence_golden.json'

_UUID_RE = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    r'|(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])'
    # 16-hex fast_id: quote-bounded (full JSON string value only) so the
    # 16-digit runs inside float reprs can never match
    r'|(?<=")[0-9a-f]{16}(?=")', re.I)
_UID_FIELD_RE = re.compile(r'("uid": ")([0-9a-f]{6,32})(")', re.I)


def _json_default(o):
    """Full-fidelity serialization for numpy payload members (default=str
    would ellipsis-summarize large arrays, blinding the oracle to the
    control-envelope buffer)."""
    import numpy as np
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return str(o)


def normalize_payload(payload) -> str:
    """Serialize a lowered payload with per-process ids replaced by
    first-appearance ordinals (events, voices, and meta.inserts uids)."""
    s = json.dumps(payload, sort_keys=True, indent=1, default=_json_default)
    seen = {}

    def ordinal(u):
        if u not in seen:
            seen[u] = f'UUID{len(seen)}'
        return seen[u]

    s = _UUID_RE.sub(lambda m: ordinal(m.group(0)), s)
    s = _UID_FIELD_RE.sub(lambda m: m.group(1) + ordinal(m.group(2)) + m.group(3), s)
    return s


def _inst(name, defName='kl_tri', has_gate=True, **pf):
    defaults = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'out': 0}
    if has_gate:
        defaults['gate'] = 1
    defaults.update(pf)
    return SynthDefInstrument(name=name, defName=defName, pfields=defaults)


def build_miniature_score() -> Score:
    """Deterministic miniature score covering the lowering surfaces."""
    lead = _inst('lead')
    pad = _inst('pad', freq=220.0)
    pluck = _inst('pluck', has_gate=False)
    kit = Kit({
        'kick': _inst('kick', defName='kl_kicktone', freq=60.0),
        'snare': _inst('snare', defName='kl_noisebpf', freq=200.0),
    })

    # -- melodic UC: rests, a tie, a slur, poly pfields, per-leaf overrides
    mel = UC(tempus='5/8', prolatio=(2, -1, (1, (1, 1, 1)), (1, (1, 1.0))),
             beat='1/8', bpm=112, inst=lead, pfields=['amp'])
    leaves = set(mel._rt.leaf_nodes)
    slur_branch = next(
        n for n in mel._rt.nodes
        if n not in leaves and n != mel._rt.root
        and all(c in leaves for c in mel._rt.successors(n))
        and len(mel._rt.successors(n)) == 3)
    mel.apply_slur(node=slur_branch)
    first_leaf = tuple(mel._rt.leaf_nodes)[0]
    mel.set_pfields(first_leaf, freq=(330.0, 415.0), amp=0.22)  # poly pfield
    mel.root.set_pfields(pan=-0.25)                     # parent-level override

    # -- pad UC with a baked (non-control) envelope and a control envelope
    pad_uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=112,
                inst=pad, pfields=['amp'])
    pad_uc.apply_envelope(Envelope([0.1, 0.5], times=[2.0]), 'amp',
                          node=pad_uc._rt.root)
    pad_uc.apply_envelope(Envelope([0.0, 1.0, 0.3], times=[1.0, 2.0]), 'pan',
                          node=pad_uc._rt.root, control=True)

    # -- kit UC (family/round-robin lowering path)
    drums = UC(tempus='4/4', prolatio=(1, 1, 1, 1, 1, 1, 1, 1), beat='1/4',
               bpm=112, inst=kit)

    # -- one-shot (gateless) UC
    plk = UC(tempus='3/4', prolatio=(1, -2, 3), beat='1/4', bpm=112,
             inst=pluck, pfields=['amp'])

    # -- bare TemporalUnits (exercise Score's UT->UC auto-promotion, both
    # standalone and mixed into a container)
    bare_ut = UT(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=112)

    # -- containers: UTS + BT on all three axes, nested
    seq = UTS([mel.copy(), plk.copy(), UT(tempus='2/4', prolatio=(1, -1),
                                          beat='1/4', bpm=112)])
    block_left = BT([drums.copy(), pad_uc.copy()], axis=-1)
    block_center = BT([mel.copy(), plk.copy()], axis=0)
    block_right = BT([seq, block_center], axis=1)

    score = Score()
    score.track('main', inserts=[SynthDefFX('kl_reverb', mix=0.4, room=0.7)])
    score.track('dry')
    score.add(block_left, name='groove', track='main')
    score.add(block_right, name='melody', track='dry', at=-1.5)  # negative time
    score.add(pad_uc, name='pad_tail', after='groove')
    score.add(Event(inst=_inst('hit', has_gate=False), dur=0.5,
                    pfields={'freq': 880.0, 'amp': 0.3}),
              name='loose_hit', at=2.25)
    score.add(bare_ut, name='bare_promotion', at=1.0)
    return score


def lower(score: Score) -> dict:
    return convert_score_to_sc_events(score)


# ---------------------------------------------------------------------------


class TestGoldenPayload:
    def test_build_is_deterministic(self):
        a = normalize_payload(lower(build_miniature_score()))
        b = normalize_payload(lower(build_miniature_score()))
        assert a == b

    def test_payload_matches_golden(self):
        assert GOLDEN_PATH.exists(), (
            f'{GOLDEN_PATH} missing — regenerate with '
            f'`python tests/test_lowering_equivalence.py --regen`')
        got = normalize_payload(lower(build_miniature_score()))
        want = GOLDEN_PATH.read_text()
        if got != want:
            for i, (ca, cb) in enumerate(zip(want, got)):
                if ca != cb:
                    lo, hi = max(0, i - 100), i + 100
                    pytest.fail(
                        'payload deviates from golden fixture at byte '
                        f'{i}:\n golden: ...{want[lo:hi]}...\n'
                        f' got:    ...{got[lo:hi]}...')
            pytest.fail(f'payload length changed: {len(want)} -> {len(got)}')

    def test_payload_ids_unique(self):
        """'new' events must carry process-unique ids; every other event
        type ('set' for SLUR continuations, 'release') deliberately reuses
        the id of the synth it targets, so those must reference a known
        spawn. (Tie continuations emit no event at all -- the group lowers
        to one merged 'new'.) Insert-FX uids must be unique and disjoint
        from event ids."""
        payload = lower(build_miniature_score())
        new_ids = [e['id'] for e in payload['events']
                   if e.get('type') == 'new' and 'id' in e]
        assert new_ids, 'expected new events with ids'
        assert len(new_ids) == len(set(new_ids)), 'duplicate spawn ids'
        other_ids = {e['id'] for e in payload['events']
                     if e.get('type') != 'new' and 'id' in e}
        assert other_ids, 'expected slur-continuation set events'
        assert other_ids <= set(new_ids), \
            'non-new event referencing unknown spawn id'
        fx_uids = []
        inserts = payload.get('meta', {}).get('inserts', {}) or {}
        for chain in inserts.values():
            fx_uids.extend(fx['uid'] for fx in chain if 'uid' in fx)
        assert len(fx_uids) == len(set(fx_uids)), 'duplicate insert uids'
        assert not (set(fx_uids) & set(new_ids)), \
            'insert uid collides with event id'


class TestHandComputedAnchor:
    """One number here is NOT read off the pipeline.

    Everything else in this module is either characterization (the golden) or
    self-consistency (``f(x) == f(x)``, byte-identical copy paths, id
    uniqueness), so ``--regen`` silences all of it: a golden regenerated over a
    behaviour change pins the code to itself. This value is derived by hand
    from ``build_miniature_score`` and cannot be regenerated away.

    The derivation: ``loose_hit`` is added at score time ``2.25`` with
    ``dur=0.5``. The earliest thing in the score is ``block_right`` at
    ``-1.5``, and a timeline that begins below zero is pulled up to start at 0
    during lowering (the documented ``start_time=None`` rule on
    ``Score.export``). So the hit lands at ``2.25 - (-1.5) == 3.75``, and the
    whole payload starts at 0.

    It is ONE anchor on absolute placement, not a second oracle. It says
    nothing about pitch, amplitude, envelopes, ties, slurs, or ordering -- the
    golden is still the only thing watching those, with the weakness the module
    docstring describes.
    """

    def test_the_loose_events_absolute_time_is_hand_derivable(self):
        payload = lower(build_miniature_score())
        hits = [e for e in payload['events']
                if (e.get('pfields') or {}).get('freq') == 880.0]
        assert len(hits) == 1, 'the 880 Hz one-shot identifies loose_hit'
        assert hits[0]['start'] == pytest.approx(3.75)
        assert hits[0]['dur'] == pytest.approx(0.5)
        assert min(e['start'] for e in payload['events']) == pytest.approx(0.0)


class TestFastIdGenerator:
    def test_ids_unique_across_concurrent_conversions(self):
        """Two conversions running interleaved (threads) must never mint
        colliding ids — the uuid-prefix + shared-counter scheme depends
        on the counter being atomic."""
        import threading
        from klotho.utils.ids import fast_id
        results = [[] for _ in range(4)]

        def mint(bucket):
            bucket.extend(fast_id() for _ in range(5000))

        threads = [threading.Thread(target=mint, args=(b,)) for b in results]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        all_ids = [i for b in results for i in b]
        assert len(all_ids) == len(set(all_ids))
        assert all(len(i) == 16 for i in all_ids[:10])

    def test_two_conversions_share_no_ids(self):
        a = lower(build_miniature_score())
        b = lower(build_miniature_score())
        ids_a = {e['id'] for e in a['events'] if 'id' in e}
        ids_b = {e['id'] for e in b['events'] if 'id' in e}
        assert not (ids_a & ids_b)


class TestCopyEquivalence:
    def test_fast_copy_vs_rebuild_byte_identical(self, monkeypatch):
        fast = normalize_payload(lower(build_miniature_score()))
        monkeypatch.setattr(UT, 'copy', UT._copy_rebuild)
        monkeypatch.setattr(UC, 'copy', UC._copy_rebuild)
        legacy = normalize_payload(lower(build_miniature_score()))
        assert fast == legacy


class TestAliasing:
    def _uc(self):
        uc = UC(tempus='4/4', prolatio=(1, (1, (1, 1)), 1), beat='1/4',
                bpm=120, inst=_inst('alias_probe'), pfields=['amp'])
        uc.leaves.set_pfields(amp=0.5, freq=100.0)
        return uc

    @staticmethod
    def _score_of(uc):
        s = Score()
        s.add(uc, name='probe')
        return s

    def test_mutating_original_leaves_copy_intact(self):
        uc = self._uc()
        c = uc.copy()
        before = normalize_payload(lower(self._score_of(c)))
        uc.leaves.set_pfields(amp=0.9, freq=999.0)
        uc.make_rest(0)
        after = normalize_payload(lower(self._score_of(c)))
        assert before == after

    def test_mutating_copy_leaves_original_intact(self):
        uc = self._uc()
        before = normalize_payload(lower(self._score_of(uc)))
        c = uc.copy()
        c.leaves.set_pfields(amp=0.9, freq=999.0)
        c.make_rest(0)
        after = normalize_payload(lower(self._score_of(uc)))
        assert before == after

    def test_parent_level_set_propagates_on_copy(self):
        """Copies preserve override *placement*: a parent-level write on
        the copy still reaches leaves that had no leaf-level override
        (the legacy rebuild flattened effective values, which silently
        broke this)."""
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120,
                inst=_inst('prop_probe'), pfields=['amp'])
        uc.root.set_pfields(amp=0.4)
        c = uc.copy()
        c.root.set_pfields(amp=0.7)
        assert [e['amp'] for e in c] == [0.7, 0.7]
        # and the original is untouched
        assert [e['amp'] for e in uc] == [0.4, 0.4]


if __name__ == '__main__':
    import sys
    if '--regen' in sys.argv:
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(normalize_payload(lower(build_miniature_score())))
        print(f'golden regenerated: {GOLDEN_PATH}')
    else:
        print(__doc__)

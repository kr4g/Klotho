"""ENV-9 part A: ``insert`` and ``extract`` move every onset without rebaking.

A control envelope's stored values are computed against the leaves' real
onsets. The preserved-family verbs rewrite the whole leaf surface through
``_respell`` -- every onset moves -- but the rebake gate only opens for an
announcement from ``_announce_leaf_surface_change``, and none of these three
verbs made one. So an envelope went on holding values computed for durations
that no longer existed.

Measured on a four-beat unit under a 0->1 ramp::

    insert    amps [0.1, 0.0, 0.25, 0.5, 0.75]   the new leaf has no envelope
                                                 value and the ramp starts
                                                 after it
    extract   amps [0.25, 0.5, 0.75]             the ramp never reaches its
                                                 own start
    scale     amps [0.0, 0.25, 0.5, 0.75]        unchanged, while onsets went
                                                 1.333 -> 0.571

This was already incoherent with its own neighbour: subdividing a leaf the
envelope never named rebakes correctly, while ``insert``, which moves every
onset the envelope depends on, did not.

``scale`` IS NOT FIXED HERE and that is deliberate. Its id relocation is the
identity, so the ``baked_leaves`` gate -- which compares resolved leaf ID
sequences, never timings -- correctly reports "nothing changed" while every
onset moved. Fixing it means re-keying that gate on timing, and the gate
exists to hold a ruled property: an edit outside an envelope's span must not
re-assert it over values written later. That is a design call, not a
measurement, so it is filed as ENV-9 part B and named in the guard's
allowlist rather than quietly left out.
"""

import warnings

import pytest

from klotho.dynatos.envelopes import Envelope
from klotho.thetos import CompositionalUnit as UC


def _ramped():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
            pfields={'amp': 0.1})
    leaves = list(uc._rt.leaf_nodes)
    uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp', node=leaves,
                      control=True)
    return uc


def _amps(uc):
    return [round(v, 6) for v in uc.events['amp']]


class TestTheEnvelopeFollowsARespell:

    def test_insert_gives_every_leaf_a_value_on_the_curve(self):
        uc = _ramped()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.insert(0, '1/4')

        amps = _amps(uc)
        assert amps == sorted(amps), (
            f'the ramp is no longer monotonic across the new surface: {amps}')
        assert amps[0] == 0.0, (
            f'the inserted leaf sits before the curve start: {amps}')

    def test_extract_keeps_the_curve_anchored_to_its_own_ends(self):
        uc = _ramped()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.extract(0)

        amps = _amps(uc)
        assert amps[0] == 0.0, (
            f'the ramp no longer starts where the envelope starts: {amps}')

    @pytest.mark.parametrize('verb', ['insert', 'extract'])
    def test_the_baked_leaves_match_what_the_envelope_now_resolves_to(self, verb):
        uc = _ramped()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            if verb == 'insert':
                uc._rt.insert(0, '1/4')
            else:
                uc._rt.extract(0)

        for desc in uc._control_envelopes.values():
            resolved = tuple(uc._resolve_control_envelope_leaves(desc))
            assert tuple(desc['baked_leaves']) == resolved


class TestScaleIsKnowinglyLeftOut:
    """A test that PINS a known gap rather than a fix.

    It exists so the gap cannot be closed by accident and then forgotten, and
    so that whoever takes ENV-9 part B finds a red test waiting rather than a
    silent success. If this starts failing, the gate was re-keyed and part B
    is done -- delete it and say so.
    """

    def test_scale_still_does_not_rebake(self):
        uc = _ramped()
        before = _amps(uc)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.scale(0, '1/2')

        assert _amps(uc) == before, (
            'scale now rebakes -- ENV-9 part B has been done, so this pin and '
            'the allowlist entry naming it should both go')

"""The rebake gate, and the two ways it can be wrong.

``_queue_envelope_rebakes`` decides whether a structural edit re-asserts a
control envelope over its leaves. Both failure directions cost something real
and neither is caught by a suite count:

* **Rebaking too much** overwrites values written AFTER the envelope. Commit
  ``784a3b5`` paid for this once already -- a later ``control=False`` envelope
  on the same pfield was silently reverted, and a ``Bind`` stored inside the
  span was replaced by the float it happened to evaluate to, so the callable
  never ran again. Ryan's ENV-6 ruling promises those resolve last-write-wins.
* **Rebaking too little** leaves a leaf inside a live envelope carrying a
  value computed against durations that no longer exist, or no value at all --
  a hole in the ramp.

The gate is therefore tested in BOTH directions here, because a gate that can
only fail one way is half a gate.

The defect these tests were written against: ``_remap_control_envelopes``
remapped ``anchor_node`` and ``leaf_subset`` through the id mapping but never
``baked_leaves``. So after any id-relocating edit the gate compared NEW leaf
ids against OLD ones, never matched, and re-asserted an envelope the edit had
not touched -- resurrecting both halves of the ``784a3b5`` regression through
a door that commit never covered. It reproduces on an ordinary insert near the
top of the bar, not on anything exotic.
"""

import warnings

import pytest

from klotho.dynatos.envelopes import Envelope
from klotho.thetos import Bind, CompositionalUnit as UC


def _uc_with_envelope_over_the_tail():
    """Four beats; a control envelope over the last two only.

    The envelope deliberately does NOT cover the whole bar, so an edit at the
    top of the bar is provably outside its span.
    """
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
            pfields={'amp': 0.1})
    leaves = list(uc._rt.leaf_nodes)
    uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp',
                      node=[leaves[2], leaves[3]], control=True)
    return uc, leaves


def _amps(uc):
    return list(uc.events['amp'])


class TestAnEditOutsideTheSpanDoesNotReassertTheEnvelope:
    """The property ``784a3b5`` restored, defended at the relocation door.

    A composer writes an envelope, then overrides two notes by hand, then
    inserts a note somewhere else entirely. Their overrides must survive: the
    hand-written value is the LATER write, and ENV-6 says the later write
    wins.
    """

    def test_a_later_explicit_write_survives_an_unrelated_insert(self):
        uc, leaves = _uc_with_envelope_over_the_tail()
        uc.set_pfields(leaves[2], amp=0.9)
        uc.set_pfields(leaves[3], amp=0.95)
        before = _amps(uc)
        assert before[-2:] == [0.9, 0.95], 'fixture did not take'

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.insert_child(uc._rt.root, 1, proportion=1)

        after = _amps(uc)
        assert after[-2:] == [0.9, 0.95], (
            f'an insert at the top of the bar reverted the user\'s own later '
            f'writes: {before} -> {after}'
        )

    def test_a_bind_inside_the_span_is_not_replaced_by_a_scalar(self):
        """The second half of the same regression. A ``Bind`` that survives
        as a stored callable keeps running; one flattened to the float it
        happened to evaluate to never runs again, and nothing says so."""
        uc, leaves = _uc_with_envelope_over_the_tail()
        uc.set_pfields(leaves[3], amp=Bind(lambda ctx: 0.42))
        stored = uc._rt[leaves[3]]['amp']
        assert isinstance(stored, Bind), 'fixture did not take'

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.insert_child(uc._rt.root, 1, proportion=1)

        survivor = [n for n in uc._rt.leaf_nodes
                    if isinstance(uc._rt[n].get('amp'), Bind)]
        assert survivor, 'the Bind was flattened to a scalar by a spurious rebake'

    def test_baked_leaves_follows_the_ids_it_names(self):
        """The mechanism, pinned directly so the next reader sees WHY.

        ``baked_leaves`` records which leaves the stored values were computed
        for. If the ids move and it does not move with them, the gate is
        comparing two different address spaces and can only ever answer
        'changed'.
        """
        uc, leaves = _uc_with_envelope_over_the_tail()
        (desc,) = uc._control_envelopes.values()
        assert tuple(desc['baked_leaves']) == tuple(desc['leaf_subset'])

        captured = {}
        original = UC._queue_envelope_rebakes

        def spy(self, descriptors):
            for d in descriptors:
                captured.setdefault('seen', []).append(
                    (tuple(d.get('baked_leaves') or ()),
                     tuple(self._resolve_control_envelope_leaves(d))))
            return original(self, descriptors)

        UC._queue_envelope_rebakes = spy
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                uc._rt.insert_child(uc._rt.root, 1, proportion=1)
        finally:
            UC._queue_envelope_rebakes = original

        for baked, resolved in captured.get('seen', []):
            assert baked == resolved, (
                f'the gate saw baked_leaves={baked} against resolved '
                f'{resolved} -- two address spaces, so it can only say '
                f'"changed"'
            )


class TestAnEditInsideTheSpanStillRebakes:
    """The other direction. Fixing the over-rebake must not buy silence.

    A gate tuned so tight it never fires leaves a sounding leaf mid-span with
    a value computed for durations that no longer exist -- or with no value at
    all, which is the hole in the ramp the over-rebake was paid for.
    """

    @pytest.mark.parametrize('handle', ['uc', 'raw'])
    def test_growing_a_target_extends_the_ramp_onto_the_new_leaves(self, handle):
        """Asserted on VALUES, not on bookkeeping, and that distinction was
        earned.

        The first version of this test asserted ``baked_leaves == resolved``.
        A mutation that remaps ``baked_leaves`` by EXPANDING it through growth
        -- an over-tight gate, the opposite error -- satisfies that assertion
        by construction and left the test green while the ramp flattened.
        Measured under that mutation: ``[0.1, 0.1, 0.0, 0.5, 0.5]``, the
        grown leaf's value merely COPIED onto both children by
        ``UC.subdivide``'s own pfield copy, where the curve says
        ``[0.1, 0.1, 0.0, 0.5, 0.75]``. A gate that stops firing when
        membership genuinely changed is the hole in the ramp SLUR-1 already
        paid for once.
        """
        uc, leaves = _uc_with_envelope_over_the_tail()
        before = _amps(uc)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            if handle == 'uc':
                uc.subdivide(leaves[3], (1, 1))
            else:
                uc._rt.subdivide(leaves[3], (1, 1))

        amps = _amps(uc)
        assert all(a is not None for a in amps), 'a leaf mid-span has no value'
        assert amps[-1] > amps[-2], (
            f'{handle}: the ramp flattened instead of continuing over the new '
            f'leaf -- {before} -> {amps}'
        )
        assert amps[-1] > before[-1], (
            f'{handle}: the curve never reaches further than it did before the '
            f'span grew -- {before} -> {amps}'
        )

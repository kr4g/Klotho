"""An overlay splits at an instrument change.

Ryan, 2026-08-31: *"Part of the 'smart' behavior for slurs is to detect
instrument changes. Slurs only make sense across the same instrument. Same
with control envs. Use common sense."*

**What counts as "the same instrument"** (his follow-up ruling, against the
measurements below): the resolved instrument, compared by the ties charter's
own predicate ``_tie_instruments_join`` -- §5's ``instrument_key`` component,
already implemented for tie joining -- PLUS the ``group`` mfield, because the
scheduler re-points the out bus by group and a slur additionally pools voices
at lowering, so a cross-track slur carries the hazard a cross-track tie
carries.

The rest of §5's composite key is deliberately OUT, and that is a decision
against the recorded default of "reuse R15 whole":

* ``kit_voice_key`` differs between consecutive leaves of a rotating family
  BY CONSTRUCTION (§5 says so), so reusing it would shatter every slur over a
  kit passage into single-note runs -- and a run under two members dissolves,
  silently destroying an authored slur. Measured: the lowering already sounds
  that same passage as ONE synth with no warning.
* ``voice_count`` would split a slur running from a single note into a double
  stop, which is ordinary notation. A tie needs matching arity because it
  MERGES two notes into one sound; a slur merges nothing, and the slur
  lowering already expands every event in an arc to the group maximum
  precisely so the voice count never changes mid-slur.

**Where it is enforced: three sites, not one.** Authoring
(``apply_slur``/``apply_envelope``), the structural heal, and
``set_instrument`` itself. The third was not obvious and is not optional:
measured, ``set_instrument`` on a leaf inside a live arc bumped
``_instruments_version`` and ran no heal at all, so an authoring-time split
alone left the arc spanning two instruments the moment anyone bound after
drawing.

**A split envelope keeps its values** (Ryan's ruling): each half holds the
slice of the curve it already had, so a crescendo still ramps continuously
across the split and only the bookkeeping changes. Splitting exists so that
control messages do not cross an instrument boundary, not to restart the
gesture -- two hairpins where the composer drew one is not what the passage
says. Measured before the fix, a naive split re-ran the whole curve over each
half's own sub-span and turned ``[0.1, 0.3, 0.5, 0.7]`` into
``[0.1, 0.5, 0.1, 0.5]``.

**And refusal is an answer** (Ryan, same day): *"we can certainly have 'sorry,
you can't do that' warnings/errors where appropriate. We don't need to
accommodate every application, especially when it doesnt make sense."* So a
two-note slur whose notes are on different instruments raises, rather than
silently returning an empty list the way the analogous all-rest case does.
"""

import warnings

import pytest

from klotho.dynatos.envelopes import Envelope
from klotho.thetos import CompositionalUnit as UC


def _four_beats(pfields=None):
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
            pfields=pfields if pfields is not None else {'freq': 440})
    return uc, list(uc._rt.leaf_nodes)


def _bind(uc, leaves, *names):
    for leaf, name in zip(leaves, names):
        if name is not None:
            uc.set_instrument(leaf, name)


def _arcs(uc):
    return sorted(tuple(spec['leaf_nodes'])
                  for spec in uc._slur_specs.values())


class TestASlurSplitsAtAnInstrumentChange:

    def test_authoring_across_a_change_gives_two_arcs(self):
        uc, leaves = _four_beats()
        _bind(uc, leaves, 'kl_saw', 'kl_saw', 'kl_tri', 'kl_tri')

        uc.apply_slur(leaves)

        assert _arcs(uc) == [(leaves[0], leaves[1]), (leaves[2], leaves[3])]

    def test_a_two_note_slur_across_a_change_refuses(self):
        """Ruling: 'sorry, you can't do that'. Nothing authorable survives,
        and the analogous all-rest path returns a silent empty list, which
        hands the caller no slur and no reason."""
        uc, leaves = _four_beats()
        _bind(uc, leaves, None, 'kl_saw', 'kl_tri', None)

        with pytest.raises(ValueError, match='instrument'):
            uc.apply_slur([leaves[1], leaves[2]])

    def test_a_track_change_splits_it_too(self):
        """``group`` is in the identity for the reason §5 puts it there: the
        scheduler re-points the out bus by group."""
        uc, leaves = _four_beats()
        for leaf in leaves:
            uc.set_instrument(leaf, 'kl_saw')
        uc.set_mfields(leaves[2], group='perc')
        uc.set_mfields(leaves[3], group='perc')

        uc.apply_slur(leaves)

        assert _arcs(uc) == [(leaves[0], leaves[1]), (leaves[2], leaves[3])]

    def test_unbound_leaves_do_not_split(self):
        """UNBOUND is its own kind and joins itself -- never silently the
        default synth. Four unbound notes are one phrase, not four."""
        uc, leaves = _four_beats()

        uc.apply_slur(leaves)

        assert _arcs(uc) == [tuple(leaves)]

    def test_binding_the_whole_selection_alike_does_not_split(self):
        uc, leaves = _four_beats()
        _bind(uc, leaves, 'kl_saw', 'kl_saw', 'kl_saw', 'kl_saw')

        uc.apply_slur(leaves)

        assert _arcs(uc) == [tuple(leaves)]

    def test_an_inherited_binding_counts_as_the_same_instrument(self):
        """Comparison is on the RESOLVED walk, never on binding presence:
        adjacent leaves routinely agree purely by inheritance (§5)."""
        uc, leaves = _four_beats()
        uc.set_instrument(uc._rt.root, 'kl_saw')
        uc.set_instrument(leaves[1], 'kl_saw')

        uc.apply_slur(leaves)

        assert _arcs(uc) == [tuple(leaves)]


class TestSetInstrumentSplitsALiveOverlay:
    """The third enforcement site. Without it the ruling cannot hold: bind
    after drawing and the arc quietly spans two instruments."""

    def test_binding_a_member_splits_the_arc(self):
        uc, leaves = _four_beats()
        for leaf in leaves:
            uc.set_instrument(leaf, 'kl_saw')
        uc.apply_slur(leaves)
        assert _arcs(uc) == [tuple(leaves)]

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc.set_instrument([leaves[2], leaves[3]], 'kl_tri')

        assert _arcs(uc) == [(leaves[0], leaves[1]), (leaves[2], leaves[3])]

    def test_a_change_that_leaves_no_arc_dissolves_it_and_says_so(self):
        uc, leaves = _four_beats()
        uc.set_instrument(leaves[1], 'kl_saw')
        uc.set_instrument(leaves[2], 'kl_saw')
        uc.apply_slur([leaves[1], leaves[2]])

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            uc.set_instrument(leaves[2], 'kl_tri')

        assert _arcs(uc) == []
        assert any('Slur removed' in str(w.message) for w in caught), (
            f'silent: {[str(w.message) for w in caught]}')

    def test_binding_one_leaf_at_a_time_is_not_the_same_as_binding_both(self):
        """And that is deliberate, not a rounding error.

        Each edit heals against the music that exists at that moment
        (SLUR-A5), and a split overlay STAYS split -- the doctrine
        ``make_sounding`` already states for rests: "A split slur stays
        split and a dropped envelope stays dropped; re-apply them if you
        want them back." So binding beat 3 alone strands beat 4 on its own,
        and binding beat 4 afterwards does not re-form the arc.
        """
        together, leaves = _four_beats()
        for leaf in leaves:
            together.set_instrument(leaf, 'kl_saw')
        together.apply_slur(leaves)

        apart, other = _four_beats()
        for leaf in other:
            apart.set_instrument(leaf, 'kl_saw')
        apart.apply_slur(other)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            together.set_instrument([leaves[2], leaves[3]], 'kl_tri')
            apart.set_instrument(other[2], 'kl_tri')
            apart.set_instrument(other[3], 'kl_tri')

        assert _arcs(together) == [(leaves[0], leaves[1]),
                                   (leaves[2], leaves[3])]
        assert _arcs(apart) == [(other[0], other[1])]

    def test_binding_outside_the_arc_leaves_it_alone(self):
        uc, leaves = _four_beats()
        for leaf in leaves:
            uc.set_instrument(leaf, 'kl_saw')
        slur_id = uc.apply_slur([leaves[1], leaves[2]])

        uc.set_instrument(leaves[0], 'kl_tri')

        assert slur_id in uc._slur_specs
        assert _arcs(uc) == [(leaves[1], leaves[2])]

    def test_the_mid_slur_instrument_warning_becomes_a_path_that_never_fires(self):
        """The warning shipped in a36c198 announced that a mid-slur
        instrument change is ignored at lowering. Under this ruling the
        situation it announces cannot be constructed any more, so it is kept
        as a guard and a firing is a bug."""
        uc, leaves = _four_beats()
        for leaf in leaves:
            uc.set_instrument(leaf, 'kl_saw')
        uc.apply_slur(leaves)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            uc.set_instrument(leaves[2], 'kl_tri')
            uc.events

        offenders = [str(w.message) for w in caught
                     if 'instrument' in str(w.message).lower()
                     and 'slur' in str(w.message).lower()]
        assert not offenders, offenders


class TestAnEnvelopeSplitsAndKeepsItsValues:

    @staticmethod
    def _ramped(uc, leaves):
        return uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp',
                                 node=leaves, control=True)

    def test_the_values_are_unchanged_by_the_split(self):
        """The ruling, stated as the test that would catch its opposite. A
        split that re-runs the whole curve over each half turns the measured
        ramp into two half-ramps."""
        uniform, leaves = _four_beats({'amp': 0.1})
        for leaf in leaves:
            uniform.set_instrument(leaf, 'kl_saw')
        self._ramped(uniform, leaves)
        one_curve = list(uniform.events['amp'])
        assert len(set(one_curve)) == 4, f'fixture is not a ramp: {one_curve}'

        split, leaves = _four_beats({'amp': 0.1})
        _bind(split, leaves, 'kl_saw', 'kl_saw', 'kl_tri', 'kl_tri')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self._ramped(split, leaves)

        assert list(split.events['amp']) == one_curve, (
            f'the split restarted the ramp: {one_curve} -> '
            f'{list(split.events["amp"])}'
        )

    def test_it_becomes_two_descriptors(self):
        uc, leaves = _four_beats({'amp': 0.1})
        _bind(uc, leaves, 'kl_saw', 'kl_saw', 'kl_tri', 'kl_tri')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self._ramped(uc, leaves)

        assert len(uc._control_envelopes) == 2
        covered = sorted(n for d in uc._control_envelopes.values()
                         for n in (d['leaf_subset'] or ()))
        assert covered == sorted(leaves)

    def test_an_envelope_keeps_its_own_constraints(self):
        """Envelopes absorb like slurs and split like slurs, and share
        nothing else. A single surviving target is still an envelope -- the
        ">= 2 members" rule is a property of what a SLUR is, and copying it
        across by symmetry would be a different feature in this one's
        clothes."""
        uc, leaves = _four_beats({'amp': 0.1})
        _bind(uc, leaves, 'kl_saw', 'kl_tri', 'kl_tri', 'kl_tri')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self._ramped(uc, leaves[:2])

        assert len(uc._control_envelopes) == 2, (
            'a one-leaf run is still a legitimate envelope')

    def test_set_instrument_splits_a_live_envelope_too(self):
        uc, leaves = _four_beats({'amp': 0.1})
        for leaf in leaves:
            uc.set_instrument(leaf, 'kl_saw')
        self._ramped(uc, leaves)
        before = list(uc.events['amp'])

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc.set_instrument([leaves[2], leaves[3]], 'kl_tri')

        assert len(uc._control_envelopes) == 2
        assert list(uc.events['amp']) == before, (
            f'splitting a live envelope changed what it sounds: {before} -> '
            f'{list(uc.events["amp"])}')


class TestTheStructuralHealSplitsToo:
    """The site Ruling B names alongside authoring, and the one a structural
    edit reaches: growth inherits its parent's instrument, so absorb cannot
    itself create a mismatch -- but ``move_subtree`` and ``graft_subtree``
    carry bindings in with them.

    Measured before this landed: moving a ``kl_tri`` leaf into a ``kl_saw``
    arc left the arc stored as two members on two different instruments,
    which is exactly the state the ruling forbids and the state the lowering
    warning was written to announce.
    """

    @staticmethod
    def _mixed_by_moving():
        uc = UC(tempus='6/4', prolatio=(1,) * 6, beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        for leaf in leaves:
            uc.set_instrument(leaf, 'kl_saw')
        uc.set_instrument(leaves[4], 'kl_tri')
        uc.apply_slur([leaves[0], leaves[1]])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.move_subtree(leaves[4], leaves[1])
        return uc

    def test_no_arc_survives_spanning_two_instruments(self):
        uc = self._mixed_by_moving()

        for slur_id, spec in uc._slur_specs.items():
            instruments = [uc.get_instrument(n) for n in spec['leaf_nodes']]
            assert len(set(map(repr, instruments))) == 1, (
                f'arc {slur_id} spans {instruments}')

    def test_an_envelope_healed_across_a_change_splits_as_well(self):
        uc = UC(tempus='6/4', prolatio=(1,) * 6, beat='1/4', bpm=60,
                pfields={'amp': 0.1})
        leaves = list(uc._rt.leaf_nodes)
        for leaf in leaves:
            uc.set_instrument(leaf, 'kl_saw')
        uc.set_instrument(leaves[4], 'kl_tri')
        uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp',
                          node=[leaves[0], leaves[1]], control=True)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.move_subtree(leaves[4], leaves[1])

        for env_id, desc in uc._control_envelopes.items():
            resolved = uc._resolve_control_envelope_leaves(desc)
            instruments = [uc.get_instrument(n) for n in resolved]
            assert len(set(map(repr, instruments))) <= 1, (
                f'envelope {env_id} spans {instruments}')


class TestTheDocumentedRoundTripSurvivesASplit:
    """``eid = uc.apply_envelope(..., control=True)`` then later
    ``uc.remove_envelope(eid)`` is the documented idiom. The split made
    ``apply_envelope`` return a LIST whenever the span happened to cross an
    instrument change, and ``remove_envelope`` raised
    ``TypeError: unhashable type: 'list'`` on the handle it had just been
    given.

    A caller cannot be expected to know in advance whether their span crosses
    a change, so the round trip has to work either way.
    """

    def test_a_split_handle_can_be_removed(self):
        uc, leaves = _four_beats({'amp': 0.1})
        _bind(uc, leaves, 'kl_saw', 'kl_saw', 'kl_tri', 'kl_tri')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            handle = uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp',
                                       node=leaves, control=True)
            uc.remove_envelope(handle)

        assert uc._control_envelopes == {}
        assert list(uc.events['amp']) == [0.1] * 4

    def test_an_unsplit_handle_is_still_a_bare_id(self):
        """The common case must not grow a list wrapper."""
        uc, leaves = _four_beats({'amp': 0.1})
        _bind(uc, leaves, 'kl_saw', 'kl_saw', 'kl_saw', 'kl_saw')
        handle = uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp',
                                   node=leaves, control=True)

        assert isinstance(handle, int)
        uc.remove_envelope(handle)
        assert uc._control_envelopes == {}

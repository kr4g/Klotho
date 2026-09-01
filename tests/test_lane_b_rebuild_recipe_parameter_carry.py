"""REBUILD-RECIPES — ``*``, ``modulate_tempo`` and ``modulate_tempus`` must not
manufacture a pfield value the source never had.

All three verbs share one recipe: rebuild the unit from ``ut.prolationis``,
then pour the source's parameter state into it with ``_mirror_param_state``.
Each of them ALSO passed ``pfields=ut.pfields`` -- the sorted **list of
registered names** -- to the :class:`CompositionalUnit` constructor. The
constructor's list branch means "declare these and default them to 0.0", so
every name the source had merely *registered* (and deliberately left unset)
came back pinned to ``0.0`` at the root and inherited down to every leaf.

``0.0`` is not "unset", it is a value. ``amp=0.0`` is literal silence, and
``gate=0.0`` means the envelope never opens: an identity ``uc * Fraction(1, 1)``
turned a note sounding at its SynthDef default into a note that makes no sound
at all. The argument was already redundant -- ``_mirror_param_state`` calls
``dst.register_pfields(src.pfield_names)`` itself -- so the registry survives
its removal and only the 0.0 defaulting disappears.

The public ``UC(pfields=['amp'])`` form still means what it always meant; that
constructor branch is deliberately untouched.

NOT ADDRESSED HERE, and deliberately so: the same three recipes do not carry
``_bind_memo``, so a memoized stochastic ``Bind`` draw is re-rolled by an
operation documented as a true no-op. That half is a flagged design question
(does a time operator preserve draws when ``copy()`` deliberately does not?)
and is left for Ryan to rule on.
"""

from fractions import Fraction

import pytest

from klotho.chronos.temporal_units.algorithms import modulate_tempo, modulate_tempus
from klotho.thetos import CompositionalUnit as UC
from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly


def _source(inst=None):
    """A UC with ``amp`` REGISTERED but authored on one leaf only.

    Registration happens through the ordinary authoring gesture --
    ``set_pfields`` on a single leaf -- which is how a composer acquires a
    pfield name without ever asking for a root default.
    """
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60)
    if inst is not None:
        uc.set_instrument(uc._rt.root, inst)
    uc.set_pfields([h.id for h in uc.leaves][1], amp=0.5)
    return uc


def _amps(uc):
    """The raw ``amp`` column, with NaN normalised to ``None``.

    ``nan != nan``, so comparing the column by equality would pass against
    any value at all.
    """
    return [None if v != v else v for v in uc.events['amp']]


REBUILDS = [
    ('mul_identity', lambda uc: uc * Fraction(1, 1)),
    ('mul_three_halves', lambda uc: uc * Fraction(3, 2)),
    ('modulate_tempo', lambda uc: modulate_tempo(uc, Fraction(1, 4), 120)),
    ('modulate_tempus', lambda uc: modulate_tempus(uc, 1, '8/8')),
]


class TestUnsetStaysUnset:
    """A registered-but-unset pfield reads unset on the rebuilt unit."""

    @pytest.mark.parametrize('name,rebuild',
                             REBUILDS, ids=[n for n, _ in REBUILDS])
    def test_unset_leaves_do_not_materialize_zero(self, name, rebuild):
        uc = _source()
        assert _amps(uc) == [None, 0.5, None, None]
        assert _amps(rebuild(uc)) == [None, 0.5, None, None]

    @pytest.mark.parametrize('name,rebuild',
                             REBUILDS, ids=[n for n, _ in REBUILDS])
    def test_the_registry_still_survives(self, name, rebuild):
        # `pfields=` was removed from the call site; `_mirror_param_state`
        # is what keeps the name registered, and this is the pin on that.
        assert rebuild(_source()).pfields == ['amp']

    @pytest.mark.parametrize('name,rebuild',
                             REBUILDS, ids=[n for n, _ in REBUILDS])
    def test_the_source_is_not_disturbed(self, name, rebuild):
        uc = _source()
        rebuild(uc)
        assert _amps(uc) == [None, 0.5, None, None]


class TestInstrumentDefaultsSurvive:
    """With an instrument bound, an unset control keeps its SynthDef default.

    This is the audible half: ``amp`` fell from the SynthDef's own default to
    ``0.0`` -- silence -- across an operation documented as a true no-op.
    """

    @pytest.mark.parametrize('name,rebuild',
                             REBUILDS, ids=[n for n, _ in REBUILDS])
    def test_amp_is_not_pinned_to_silence(self, name, rebuild):
        before = lower_compositional_ir_to_sc_assembly(_source(inst='kl_saw'))
        after = lower_compositional_ir_to_sc_assembly(
            rebuild(_source(inst='kl_saw')))
        unset = [e for e in after
                 if e.get('type') == 'new' and e.get('start') == 0.0]
        assert unset, 'no lowered event at the first leaf'
        assert unset[0]['pfields']['amp'] != 0.0
        assert ([e['pfields'] for e in before if e.get('type') == 'new']
                == [e['pfields'] for e in after if e.get('type') == 'new'])

    def test_identity_scaling_lowers_byte_identically(self):
        """The assertion that would have caught this: compare the LOWERING.

        The DataFrame surface alone was ambiguous -- an unset pfield reads
        NaN there and a manufactured 0.0 reads 0.0, but neither says what
        SuperCollider will be handed.
        """
        uc = _source(inst='kl_saw')
        before = lower_compositional_ir_to_sc_assembly(uc)
        after = lower_compositional_ir_to_sc_assembly(uc * Fraction(1, 1))
        assert ([e.get('pfields') for e in before]
                == [e.get('pfields') for e in after])


class TestAuthoredValuesAreUntouched:

    @pytest.mark.parametrize('name,rebuild',
                             REBUILDS, ids=[n for n, _ in REBUILDS])
    def test_an_authored_zero_is_still_carried(self, name, rebuild):
        """0.0 is a legitimate authored value and must survive as one."""
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=60)
        leaves = [h.id for h in uc.leaves]
        uc.set_pfields(leaves[0], amp=0.0)
        assert _amps(rebuild(uc)) == [0.0, None]

    def test_the_public_list_form_still_defaults_to_zero(self):
        """``UC(pfields=['amp'])`` is unchanged -- only the call sites moved."""
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=60,
                pfields=['amp'])
        assert _amps(uc) == [0.0, 0.0]
        # and a rebuild carries that real root override, because it IS set
        assert _amps(uc * Fraction(1, 1)) == [0.0, 0.0]


class TestPlainTemporalUnitIsUnaffected:

    @pytest.mark.parametrize('name,rebuild',
                             REBUILDS, ids=[n for n, _ in REBUILDS])
    def test_a_plain_unit_still_rebuilds(self, name, rebuild):
        from klotho.chronos import TemporalUnit

        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                          beat='1/4', bpm=60)
        out = rebuild(ut)
        assert len(out) == len(ut)

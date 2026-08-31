"""Regression pins for the W1 documentation wave.

A docstring cannot be tested directly, but the arithmetic and the absences it
asserts can be. These pin the claims that were wrong before the wave -- so if
the behaviour ever moves back, the wrong docstring is caught rather than
rediscovered by the next audit.
"""

import ast
import inspect
import re
from pathlib import Path

import pytest

import klotho.utils.playback as playback
from klotho.topos.graphs.lattices.lattices import Lattice
from klotho.topos.collections.sequences import Pattern
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.chronos import RhythmTree

REPO = Path(__file__).resolve().parent.parent


class TestLatticeResolutionIsABoundNotACount:
    """WL-15. The docstring said 'number of points along each dimension' and
    was wrong in both bipolar modes."""

    @pytest.mark.parametrize("n", [1, 2, 3, 5])
    def test_bipolar_gives_two_n_plus_one_points(self, n):
        lat = Lattice(dimensionality=2, resolution=n, bipolar=True)
        for axis in lat._dims:
            assert len(axis) == 2 * n + 1
            assert axis[0] == -n and axis[-1] == n

    @pytest.mark.parametrize("n", [1, 2, 3, 5])
    def test_unipolar_gives_n_plus_one_points(self, n):
        lat = Lattice(dimensionality=2, resolution=n, bipolar=False)
        for axis in lat._dims:
            assert len(axis) == n + 1
            assert axis[0] == 0 and axis[-1] == n

    def test_a_per_dimension_list_is_honoured(self):
        lat = Lattice(dimensionality=3, resolution=[2, 3, 4], bipolar=True)
        assert [len(axis) for axis in lat._dims] == [5, 7, 9]


class TestPatternTupleVersusList:
    """NEW-10."""

    def test_a_list_cycles_its_elements(self):
        p = Pattern([60, 64, 67])
        assert [next(p) for _ in range(4)] == [60, 64, 67, 60]
        assert p.length == 3

    def test_a_tuple_is_one_value_emitted_whole(self):
        p = Pattern((60, 64, 67))
        assert [next(p) for _ in range(2)] == [(60, 64, 67), (60, 64, 67)]
        assert p.length == 1

    def test_they_can_be_mixed(self):
        p = Pattern([(60, 64, 67), 72])
        assert [next(p) for _ in range(4)] == [(60, 64, 67), 72, (60, 64, 67), 72]


class TestFromManifestIsThePublicDefaultsAccessor:
    """WL-35. The item was filed as 'defaults never materialized'; the
    accessor existed. What made it look absent is that an unknown name comes
    back empty instead of raising."""

    def test_a_bundled_def_reports_its_controls(self):
        pfields = dict(SynthDefInstrument.from_manifest('kl_tri').pfields)
        assert pfields['freq'] == 440.0
        assert 'amp' in pfields and 'releaseTime' in pfields

    def test_an_unknown_name_comes_back_empty_rather_than_raising(self):
        assert dict(SynthDefInstrument.from_manifest('definitely_not_a_synth').pfields) == {}


# NEW-23's TestStaleFileHeaders was deleted 2026-08-29 (Q3, Ryan): the
# self-naming `# Klotho/klotho/...` file headers are gone, so there is
# nothing left to pin. The convention duplicated what the filesystem
# already knows and went stale on every file move -- exactly one file in
# the package had a correct one when API-3 looked.


class TestRemovedBackendsAreNotAdvertisedAsPresent:
    """RUL-02. The tombstone in _config.py and the past-tense note in the
    version-skew guard stay -- they explain live code."""

    def test_no_javascript_names_the_removed_backends_in_the_present_tense(self):
        stale = []
        for path in Path(playback.__file__).parent.rglob('*.js'):
            lines = path.read_text().split('\n')
            for i, line in enumerate(lines, 1):
                if 'tone.js' not in line.lower():
                    continue
                # A comment can wrap, so judge the sentence, not the line.
                window = ' '.join(lines[max(0, i - 3):i + 2]).lower()
                if 'removed' not in window:
                    stale.append(f"{path.name}:{i}: {line.strip()}")
        assert stale == []

    def test_the_config_tombstone_is_still_there(self):
        source = (Path(playback.__file__).parent / '_config.py').read_text()
        assert 'removed in Klotho 10.12' in source


# ----------------------------------------------------------------------------
# HAD-DOC (docket DOC-1..DOC-8). The attribution these pin was EXACTLY
# INVERTED before 2026-08-29: `autoref`, `decompose` and the rotation modes,
# the three things that genuinely reproduce Haddad's published figures, all
# cited him, while `tempus`, `prolatio`, `TemporalUnit` and `TemporalBlock`,
# which wear his vocabulary, cited nobody.
#
# An attribution that no test protects is one refactor from being lost --
# which is how the inversion arose in the first place. These are cheap and
# they are the only thing standing between the corrected record and the next
# well-meaning docstring tidy.
# ----------------------------------------------------------------------------

KLOTHO_PY = sorted((REPO / 'klotho').rglob('*.py'))


def _squash(text):
    """Collapse whitespace so a pin survives docstring re-wrapping. A
    citation that breaks the moment someone reflows a paragraph protects
    nothing."""
    return ' '.join(text.split())


class TestTheRetractedThesisTitleIsGone:
    """DOC-1. Ruling R8 cited *Vers une temporalite musicale repensee*
    ("Toward a Rethought Musical Temporality"). **That work does not exist**
    -- the phrase appears nowhere in the document. The real title is
    *L'Unite Temporelle : Une approche pour l'ecriture de la duree et de sa
    quantification* ("The Temporal Unit: An approach to the writing of
    duration and its quantification"), Sorbonne 2020, HAL tel-03258984.
    R8's verification work was sound; only the citation was wrong.

    The retracted title is allowed to appear ONLY next to a statement that
    it does not exist -- including here, and including the marker below."""

    RETRACTED = 'repens'  # matches repensee / repensée

    def test_the_package_never_names_it(self):
        hits = [p.name for p in KLOTHO_PY
                if self.RETRACTED in p.read_text().lower()]
        assert hits == []

    def test_the_only_test_mention_is_labelled_as_retracted(self):
        for path in sorted(Path(__file__).parent.rglob('*.py')):
            lines = path.read_text().split('\n')
            for i, line in enumerate(lines):
                if self.RETRACTED not in line.lower():
                    continue
                window = ' '.join(lines[max(0, i - 10):i + 6]).lower()
                assert 'does not exist' in window, f"{path.name}:{i + 1}"

    def test_the_real_citation_is_carried_where_the_terms_live(self):
        from klotho.chronos.temporal_units import temporal
        doc = _squash(temporal.__doc__)
        assert 'tel-03258984' in doc
        assert "L'Unite Temporelle" in doc
        # The rule: a French title never stands alone.
        assert 'An approach to the writing of duration' in doc


class TestTheOpenMusicPapersAreCitedAsTheEarlierSources:
    """DOC-2. The 2006 and 2008 OM Composer's Book articles PREDATE the 2020
    thesis by 12-14 years and are both in English. Anything attributing
    time-block material to "Haddad 2020" cites the derivative source."""

    def test_both_papers_are_named_with_their_years(self):
        from klotho.chronos.temporal_units import temporal
        doc = _squash(temporal.__doc__)
        assert 'The Time-Block Concept in OpenMusic' in doc and '2008' in doc
        assert 'TimeSculpt in OpenMusic' in doc and '2006' in doc

    def test_the_2008_chapter_is_named_the_primary_source(self):
        from klotho.chronos.temporal_units import temporal
        assert 'PRIMARY source' in _squash(temporal.__doc__)

    def test_the_unrecoverable_page_range_is_declared_not_invented(self):
        """Left OPEN on purpose: the printed range is not recoverable from
        the author's preprint and needs the physical volume. A blank that
        says so is worth more than a plausible invented range."""
        from klotho.chronos.temporal_units import temporal
        doc = _squash(temporal.__doc__)
        assert 'not recoverable' in doc and 'printed volume' in doc


class TestTempusProlatioAndTemporalUnitClaimHaddad:
    """DOC-3, the heart of the inversion. His terms, defined verbatim on
    p. 30 of the 2008 chapter, cited nowhere in the codebase until now."""

    def test_the_class_says_it_is_his_time_block(self):
        from klotho.chronos import TemporalUnit
        doc = _squash(TemporalUnit.__doc__)
        assert 'time-block' in doc and 'Haddad' in doc

    def test_tempus_credits_him(self):
        from klotho.chronos import TemporalUnit
        assert "Haddad's term" in _squash(TemporalUnit.tempus.__doc__)

    def test_prolationis_credits_him(self):
        from klotho.chronos import TemporalUnit
        assert "Haddad's term" in _squash(TemporalUnit.prolationis.__doc__)

    def test_the_tempo_half_is_still_claimed_as_klotho_s(self):
        """The other direction of the same duty. Haddad has NO tempo -- for
        him the Tempus fraction IS the duration -- so beat/bpm and real
        seconds must not be read as inherited from him."""
        from klotho.chronos import TemporalUnit
        assert 'no tempo' in _squash(TemporalUnit.__doc__)


class TestTemporalBlockDisclaimsALineageItDoesNotHave:
    """DOC-4. His time-block is ONE MEASURE -- tempus plus prolatio -- which
    is Klotho's TemporalUnit. A parallel stack of rows on a shared clock has
    no counterpart in Haddad at all: no such object, no such term."""

    def test_the_block_says_it_is_not_his(self):
        from klotho.chronos import TemporalBlock
        doc = _squash(TemporalBlock.__doc__)
        assert 'NOT Haddad' in doc
        assert 'Klotho-original' in doc

    def test_the_sequence_says_the_same(self):
        from klotho.chronos import TemporalUnitSequence
        assert "Klotho's own" in _squash(TemporalUnitSequence.__doc__)

    def test_principal_row_and_events_do_not_borrow_him(self):
        from klotho.chronos import TemporalBlock
        assert 'Klotho-original' in _squash(TemporalBlock.principal_row.__doc__)
        assert "Klotho's own" in _squash(TemporalBlock.events.__doc__)


class TestTheCompositionalUnitMakesTwoSeparateClaims:
    """DOC-5 / ruling R10. Envelope application follows Haddad sect8.2.2;
    the fused hierarchical parameter tree is Klotho's OWN. Collapsing the
    two is how borrowed vocabulary starts reading as borrowed design."""

    def test_the_envelope_claim_credits_him_with_a_translation(self):
        from klotho.thetos import CompositionalUnit
        doc = _squash(CompositionalUnit.__doc__)
        assert 'sect8.2.2' in doc
        assert 'reservoir de donnees quelconques' in doc
        # The rule: every French quotation carries its English inline.
        assert 'a reservoir of arbitrary data' in doc

    def test_the_parameter_tree_is_claimed_as_klotho_s(self):
        from klotho.thetos import CompositionalUnit
        doc = _squash(CompositionalUnit.__doc__)
        assert "Klotho's OWN" in doc
        # Verified as an ABSENCE, and the absence is the evidence.
        assert 'zero times' in doc

    def test_the_kept_name_carries_its_reasoning(self):
        """R10 kept the name; the reasoning has to travel with it, or the
        next reader re-opens a decision that was already made."""
        from klotho.thetos import CompositionalUnit
        doc = _squash(CompositionalUnit.__doc__)
        assert 'Nunes' in doc
        assert 'ParametricUnit' in doc and 'declined' in doc


class TestThePermuteListOffByOneIsRecordedAsDeliberate:
    """DOC-6. His Algorithm 4 rotates ``pt + 1`` times; Klotho rotates
    ``pt``. **Klotho is right** -- his own fig. 2.11 lists the identity as
    the first row, which his pseudocode as printed cannot produce. The
    behaviour and the note are pinned together, because either one alone
    invites the other to be "corrected"."""

    LST = (3, 4, 5, 7)

    def test_rotating_by_zero_is_the_identity(self):
        from klotho.topos.collections.patterns import permute_list
        assert permute_list(self.LST, 0) == self.LST

    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    def test_every_rotation_matrix_keeps_his_identity_row_first(self, mode):
        """What ``pt + 1`` would cost: row 0 of every published matrix."""
        from klotho.topos.collections.patterns import autoref, autoref_rotmat
        assert autoref_rotmat(self.LST, mode=mode)[0] == autoref(self.LST)

    def test_the_divergence_is_written_down(self):
        from klotho.topos.collections.patterns import permute_list
        doc = _squash(permute_list.__doc__)
        assert 'DELIBERATE' in doc and 'pt + 1' in doc


class TestAutoSubdivCitesTheFigureItReproduces:
    """DOC-7. It reproduces fig. 2.12 exactly and said so nowhere -- the
    mirror image of DOC-3/DOC-4: silent fidelity rather than silent
    invention."""

    def test_the_figure_is_named(self):
        from klotho.chronos.rhythm_trees.algorithms import auto_subdiv
        assert 'figure 2.12' in _squash(auto_subdiv.__doc__)

    def test_the_documented_default_is_what_the_code_does(self):
        """The docstring's claim: at n=1 each element takes its SUCCESSOR's
        value as its subdivision count, wrapping at the end."""
        from klotho.chronos.rhythm_trees.algorithms import auto_subdiv
        assert auto_subdiv((3, 4, 5)) == (
            (3, (1, 1, 1, 1)), (4, (1, 1, 1, 1, 1)), (5, (1, 1, 1)))


class TestTheHeaderNoLongerAdvertisesAShadowParameterTree:
    """DOC-8. The module header claimed CompositionalUnit "extends
    TemporalUnit with a synchronized ParameterTree" -- which the class
    docstring and CompositionalTree both explicitly deny. One fused tree."""

    def test_the_header_does_not_promise_synchronization(self):
        from klotho.thetos.composition import compositional
        doc = _squash(compositional.__doc__).lower()
        # The exact old wording. It may only survive under a denial.
        assert 'with a synchronized ``parametertree``' not in doc
        assert 'no synchronized ``parametertree``' in doc
        assert 'fused' in doc

    def test_there_is_no_shadow_tree_to_synchronize(self):
        from klotho.thetos import CompositionalUnit
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1))
        assert not hasattr(uc, '_pt')
        assert uc.rt is not uc._rt          # `rt` is a copy
        assert uc.pt is not uc.pt           # `pt` is a fresh snapshot


class TestTheAxisVocabularyIsLabelledAsKlothosCoinage:
    """Span vocabulary. The AXIS is Haddad's -- he states it on p. 128 --
    but "Tempus-preserving"/"Tempus-following" are NOT his words. His are
    « prolationnelle stricte » ("strictly prolational") and « relative »
    ("relative"). A reader who searches the thesis for the English pair
    finds nothing and concludes the code invented the distinction."""

    def test_the_english_pair_is_marked_a_coinage(self):
        from klotho.chronos.rhythm_trees import algorithms as rt_alg
        source = Path(rt_alg.__file__).read_text()
        assert 'prolationnelle stricte' in source
        assert "Klotho's coinage" in source

    def test_the_dilatation_glyph_is_boxtimes_not_odot(self):
        """His sect4.5.3 heading reads « Dilatation/Contraction (boxtimes),
        Expansion/Compression (otimes) ». Some project records carry the
        wrong glyph; the code must not."""
        joined = '\n'.join(p.read_text() for p in KLOTHO_PY)
        assert '⊠' in joined       # boxtimes, the correct one
        assert '⊙' not in joined   # odot, the records' error

    def test_erosion_is_kept_out_of_the_code(self):
        """"Erosion" was the DOCKET's coinage, not Haddad's -- his are
        *iteration simple* ("simple iteration") and *iteration recursive
        cumulative* ("cumulative recursive iteration"). Only the naming
        note may say the word."""
        hits = []
        for path in KLOTHO_PY:
            for i, line in enumerate(path.read_text().split('\n'), 1):
                low = line.lower()
                if 'erosion' in low or 'erode' in low or 'eroded' in low:
                    hits.append(f"{path.name}:{i}: {line.strip()}")
        assert [h for h in hits if 'NAMING' not in h
                and 'not Haddad' not in h
                and 'kept' not in h] == []


class TestTheTempusSpellingRulingIsMarkedReversible:
    """The preserved family never moves the authored Tempus spelling, so
    fig. 4.68 comes back ``18/18 (12 6 3 2 9)`` where Haddad prints
    ``54/54``. Same value, same durations; the denominator is a display
    choice. This is a RULING pending the client, not a settled fact, and
    the docstring has to say so or it reads as permanent."""

    def test_the_reversibility_is_written_down(self):
        from klotho.chronos import RhythmTree
        doc = _squash(RhythmTree._respell.__doc__)
        assert 'REVERSIBLE' in doc
        assert 'OPT-IN' in doc and 'pending the client' in doc

    def test_the_rule_it_replaced_is_named(self):
        """The old rule silently rewrote ``3/4`` into ``6/8`` -- the one
        pair a musician must not have interchanged. That failure is the
        whole argument for the current default."""
        from klotho.chronos import RhythmTree
        doc = _squash(RhythmTree._respell.__doc__)
        assert '3/4' in doc and '6/8' in doc

    def test_the_authored_spelling_actually_stands(self):
        from fractions import Fraction
        from klotho.chronos import RhythmTree
        rt = RhythmTree(meas='3/4', subdivisions=(1, 1, 1))
        rt.insert(1, Fraction(1, 8))
        assert str(rt.meas) == '3/4'


def _chronos_section(number):
    """The body of one numbered section of ``docs/architecture/02_CHRONOS.md``,
    heading excluded. Scoping the text pins below to a section keeps them from
    passing on a sentence that happens to appear somewhere else in the file."""
    text = (REPO / 'docs' / 'architecture' / '02_CHRONOS.md').read_text()
    parts = text.split('\n## ')
    body = [p for p in parts if p.startswith(f'{number}. ')]
    assert len(body) == 1, f'section {number} not found exactly once'
    return body[0]


class TestOnlyTheStartIsFixedAfterConstruction:
    """Two class docstrings and 02_CHRONOS.md sect5 all said a container's
    duration was "fixed after construction". It never was. A sequence's
    duration is the SUM of its members' and a block's is its LONGEST row's,
    so anything that changes membership changes the duration -- and
    ``TemporalBlock.rows`` hands out the live rows, so a row's own mutator
    moves the block's duration with no block-level mutator running at all.

    What is fixed outside a Score is the START. ``TemporalUnit`` and
    ``CompositionalUnit`` are the genuine cases and keep the claim; the
    tests below pin both halves, so a later correction cannot overshoot in
    either direction.

    Durations here are derived from the notation, not read off the code: at
    ``bpm=60`` with a quarter-note beat, a ``4/4`` measure is 4.0 s and a
    ``2/4`` measure is 2.0 s.
    """

    @staticmethod
    def _u(tempus='4/4'):
        from klotho.chronos import TemporalUnit
        return TemporalUnit(tempus=tempus, prolatio=(1, 1), bpm=60)

    def _seq(self):
        from klotho.chronos import TemporalUnitSequence
        return TemporalUnitSequence([self._u()])          # 4.0 s

    @pytest.mark.parametrize('name, mutate, expected', [
        ('append',      lambda s, u: s.append(u('2/4')),            6.0),
        ('append x2',   lambda s, u: s.append(u('2/4'), repeat=2),  8.0),
        ('prepend',     lambda s, u: s.prepend(u('2/4')),           6.0),
        ('insert',      lambda s, u: s.insert(0, u('2/4')),         6.0),
        ('remove',      lambda s, u: s.remove(0),                   0.0),
        ('replace',     lambda s, u: s.replace(0, u('2/4')),        2.0),
        ('__setitem__', lambda s, u: s.__setitem__(0, u('2/4')),    2.0),
        ('extend',      lambda s, u: s.extend(
            type(s)([u('2/4')])),                                   6.0),
    ])
    def test_every_sequence_mutator_moves_the_duration(self, name, mutate,
                                                       expected):
        seq = self._seq()
        assert seq.duration == pytest.approx(4.0)
        mutate(seq, self._u)
        assert seq.duration == pytest.approx(expected), name

    def test_the_sequence_start_is_what_stays_put(self):
        seq = self._seq()
        assert seq.start == pytest.approx(0.0)
        seq.prepend(self._u('2/4'))       # the mutator most likely to move it
        assert seq.start == pytest.approx(0.0)
        assert seq.end == pytest.approx(seq.duration)

    def test_a_live_row_mutation_moves_the_block_duration(self):
        """No block-level mutator runs here -- the sequence in row 0 is
        lengthened through its own API."""
        from klotho.chronos import TemporalBlock, TemporalUnitSequence
        blk = TemporalBlock([TemporalUnitSequence([self._u('2/4')]),
                             self._u()], axis=1, sort_rows=False)
        assert blk.duration == pytest.approx(4.0)

        blk.rows[0].append(self._u())     # row 0: 2.0 s -> 6.0 s

        assert blk.duration == pytest.approx(6.0)
        assert blk.events['end'].max() == pytest.approx(6.0)

    def test_the_block_start_is_what_stays_put(self):
        from klotho.chronos import TemporalBlock, TemporalUnitSequence
        blk = TemporalBlock([TemporalUnitSequence([self._u('2/4')]),
                             self._u()], axis=1, sort_rows=False)
        assert blk.start == pytest.approx(0.0)
        blk.rows[0].append(self._u())
        assert blk.start == pytest.approx(0.0)
        assert blk.events['start'].min() == pytest.approx(0.0)

    def test_a_unit_really_is_fixed_and_says_so(self):
        """The claim is true for exactly one of the three, which is why the
        correction had to be class by class rather than global."""
        from klotho.chronos import TemporalUnit
        unit = self._u()
        assert unit.duration == pytest.approx(4.0)
        for attr, value in (('bpm', 120), ('beat', '1/8'),
                            ('tempus', '2/4'), ('span', 2), ('duration', 1.0)):
            with pytest.raises(AttributeError):
                setattr(unit, attr, value)
        assert unit.duration == pytest.approx(4.0)
        assert 'duration is fixed after construction' in _squash(
            TemporalUnit.__doc__)

    def test_a_compositional_unit_really_is_fixed_and_says_so(self):
        from klotho.thetos import CompositionalUnit
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=60,
                               pfields=['amp'])
        assert uc.duration == pytest.approx(4.0)
        uc.set_pfields(1, amp=0.5)
        assert uc.duration == pytest.approx(4.0)
        assert 'duration is fixed after construction' in _squash(
            CompositionalUnit.__doc__)

    def test_the_sequence_docstring_no_longer_claims_a_fixed_duration(self):
        from klotho.chronos import TemporalUnitSequence
        doc = _squash(TemporalUnitSequence.__doc__)
        assert 'fixed after construction' not in doc
        assert 'always starts at time 0' in doc
        for mutator in ('append', 'prepend', 'insert', 'remove', 'replace',
                        'extend'):
            assert mutator in doc

    def test_the_block_docstring_no_longer_claims_a_fixed_duration(self):
        from klotho.chronos import TemporalBlock
        doc = _squash(TemporalBlock.__doc__)
        assert 'fixed after construction' not in doc
        assert 'always starts at time 0' in doc

    def test_the_block_docstring_says_alignment_is_lazy(self):
        """The reader list is the load-bearing part: a reader added later
        that forgets ``_ensure_aligned`` is the whole defect coming back."""
        from klotho.chronos import TemporalBlock
        doc = _squash(TemporalBlock.__doc__)
        assert '_ensure_aligned' in doc
        for reader in ('rows', 'duration', 'end', 'principal_row', 'events',
                       '__getitem__', '__iter__'):
            assert reader in doc

    def test_chronos_section_5_agrees_with_its_own_mutator_table(self):
        """The retracted sentence sat 11 lines below a table listing the six
        mutators that disprove it."""
        section = _chronos_section(5)
        assert '`append(ut, repeat=1)`' in section      # the table is still there
        assert 'is fixed after construction' not in section
        assert "sum of its members' durations" in section

    def test_chronos_section_6_documents_the_lazy_alignment(self):
        section = _chronos_section(6)
        assert '_ensure_aligned' in section
        assert 'idempotent' in section


# ----------------------------------------------------------------------------
# 12_LIFECYCLE.md section 8, the timing-cache table and state diagram.
#
# Both went stale silently. The table's `set_pfields` and `apply_envelope`
# rows flipped when d5a1b20 re-keyed `_ensure_timing_cache` from a node count
# to `_rt._structure_version`; the Score-placement and container-re-alignment
# rows flipped earlier, when 261fa4d made stored onsets offset-free. Nothing
# read the table against the code, so nothing noticed.
#
# The oracle here is the code, not the prose: every row below is MEASURED and
# the doc's verdict is asserted to match. A behaviour change therefore fails
# this file rather than quietly rotting the table again.
# ----------------------------------------------------------------------------


def _lifecycle_section(number):
    """The body of one numbered section of ``docs/architecture/12_LIFECYCLE.md``,
    heading excluded."""
    text = (REPO / 'docs' / 'architecture' / '12_LIFECYCLE.md').read_text()
    parts = text.split('\n## ')
    body = [p for p in parts if p.startswith(f'{number}. ')]
    assert len(body) == 1, f'section {number} not found exactly once'
    return body[0]


def _invalidation_table():
    """``{first cell: second cell}`` for the section-8 verdict table."""
    rows = {}
    for line in _lifecycle_section(8).split('\n'):
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 2 or set(cells[0]) <= set('- :'):
            continue
        if cells[0] == 'Operation':
            continue
        # `…` and `...` are the same row to a reader; make them the same
        # row to the matcher too, so a spelling change is not a silent miss.
        rows[cells[0].replace('…', '...')] = cells[1]
    assert rows, 'no table found in section 8'
    return rows


class TestTheTimingCacheTableMatchesMeasuredBehaviour:
    """Every row of "What Triggers Invalidation", re-derived from the code.

    ``_ensure_timing_cache`` recomputes when ``_timing_dirty`` is set OR when
    ``_timing_cache_version`` no longer equals ``_rt._structure_version``.
    That disjunction is the thing each row reports, so it is what the probes
    below evaluate -- after the operation and before any read, because a read
    clears the very state being measured.
    """

    @staticmethod
    def _uc(prolatio=(1, 1, 2, 2)):
        from klotho.chronos import TemporalUnit
        from klotho.thetos import CompositionalUnit
        return CompositionalUnit.from_ut(
            TemporalUnit(span=1, tempus='4/4', prolatio=prolatio,
                         beat='1/4', bpm=60))

    @staticmethod
    def _would_recompute(unit):
        return bool(unit._timing_dirty
                    or unit._timing_cache_version != unit._rt._structure_version)

    @classmethod
    def _measure(cls, build, operate):
        """Warm the cache, run *operate*, report whether the next read
        recomputes."""
        subject, target = build()
        target.onsets                       # warm: Dirty -> Clean
        operate(subject)
        return cls._would_recompute(target)

    # -- probes ---------------------------------------------------------
    # (row key in the doc table, builder, operation)

    @classmethod
    def _plain(cls):
        u = cls._uc()
        return u, u

    @classmethod
    def _placed(cls):
        from klotho.thetos import Score
        score = Score()
        item = score.add(cls._uc(), name='a')
        return (score, item), item.unit

    @classmethod
    def _sequence(cls):
        from klotho.chronos import TemporalUnitSequence
        seq = TemporalUnitSequence([cls._uc(), cls._uc()])
        return seq, seq._seq[1]

    @classmethod
    def _block(cls):
        from klotho.chronos import TemporalBlock
        blk = TemporalBlock([cls._uc(), cls._uc()])
        return blk, blk._rows[1]

    @staticmethod
    def _reoffset(container):
        from klotho.chronos.temporal_units.temporal import _reoffset
        _reoffset(container, 10.0)

    PROBES = [
        ('`ScoreItem.set_duration(dur)`', '_placed',
         lambda s: s[1].set_duration(16.0)),
        ('`ScoreItem.stretch(factor)`', '_placed',
         lambda s: s[1].stretch(2.0)),
        ('`make_rest(node)`', '_plain', lambda u: u.make_rest(2)),
        ('`make_sounding(node)`', '_plain',
         lambda u: (u.make_rest(2), u.make_sounding(2))),
        ('`subdivide(node, S)`', '_plain', lambda u: u.subdivide(2, (1, 1))),
        ('`graft_subtree(node, subtree)`', '_plain',
         lambda u: u.graft_subtree(
             2, __import__('klotho.chronos', fromlist=['RhythmTree'])
             .RhythmTree(span=1, meas='1/4', subdivisions=(1, 1)))),
        ('`add_child(parent, ...)`', '_plain',
         lambda u: u.add_child(0, proportion=1)),
        ('`prune(node)`', '_plain', lambda u: u.prune(3)),
        ('`remove_subtree(node)`', '_plain', lambda u: u.remove_subtree(3)),
        ('`_rt.replace_node(...)`', '_plain',
         lambda u: u._rt.replace_node(2, proportion=5)),
        ('`_rt.move_subtree(...)`', '_plain',
         lambda u: u._rt.move_subtree(2, 1)),
        ('`_rt.scale(...)`', '_plain', lambda u: u._rt.scale(1, 3)),
        ('`set_pfields(...)`', '_plain',
         lambda u: u.set_pfields(u.root, amp=0.5)),
        ('`set_mfields(...)`', '_plain',
         lambda u: u.set_mfields(u.root, group='g')),
        ('`apply_envelope(...)`', '_plain',
         lambda u: u.apply_envelope(
             __import__('klotho.dynatos', fromlist=['Envelope'])
             .Envelope.perc(), 'amp', node=u.root)),
        ('`set_instrument(...)`', '_plain',
         lambda u: u.set_instrument(
             u.root, __import__('klotho.thetos', fromlist=['Instrument'])
             .Instrument('default'))),
        ('`apply_slur(...)`', '_plain', lambda u: u.apply_slur(node=0)),
        ('Score placement', '_placed',
         lambda s: s[0].prepend(
             TestTheTimingCacheTableMatchesMeasuredBehaviour._uc(), name='b')),
        ('Container re-alignment', '_sequence', _reoffset.__func__),
        ('Container re-alignment', '_block', _reoffset.__func__),
    ]

    @pytest.mark.parametrize('key, builder, operate',
                             PROBES, ids=[p[0] for p in PROBES])
    def test_the_doc_verdict_matches_the_measurement(self, key, builder,
                                                     operate):
        recomputes = self._measure(getattr(self, builder), operate)
        table = _invalidation_table()
        matches = [(k, v) for k, v in table.items() if key in k]
        assert len(matches) == 1, (
            f'{key!r} should name exactly one table row; got {matches}')
        verdict = matches[0][1]
        expected = 'Yes' if recomputes else 'No'
        assert verdict.startswith(expected), (
            f'{key}: measured recompute={recomputes}, '
            f'table says {verdict!r}')

    def test_every_table_row_is_probed(self):
        """A row nobody measures is a row free to go stale."""
        keys = {k for k, _, _ in self.PROBES}
        unprobed = [row for row in _invalidation_table()
                    if not any(k in row for k in keys)]
        assert unprobed == []


class TestTheStateDiagramShowsBothStalenessSignals:
    """``_timing_dirty`` stopped being the whole story at d5a1b20.

    A reader debugging a stale cache who checks only the flag will conclude
    the cache is fresh in every case the version half catches -- which is
    every count-preserving mutation, the exact class of bug (RT-27) the
    version half was added for. The two tests below show each half catching
    something the other misses, so neither can be dropped from the diagram
    as redundant.
    """

    @staticmethod
    def _would_recompute(unit):
        return bool(unit._timing_dirty
                    or unit._timing_cache_version != unit._rt._structure_version)

    def test_a_count_preserving_mutation_moves_the_version_but_not_the_flag(self):
        from klotho.chronos import TemporalUnit
        unit = TemporalUnit(span=1, tempus='4/4', prolatio=(1, 1, 2),
                            beat='1/4', bpm=60)
        assert unit.durations == pytest.approx((1.0, 1.0, 2.0))
        before = unit._rt._structure_version
        unit._rt.replace_node(2, proportion=5)

        assert unit._timing_dirty is False          # the flag says "clean"
        assert unit._rt._structure_version != before
        assert self._would_recompute(unit)
        assert unit.durations == pytest.approx((0.5, 2.5, 1.0))

    def test_a_tempo_change_moves_the_flag_but_not_the_version(self):
        from klotho.thetos import Score
        from klotho.chronos import TemporalUnit
        from klotho.thetos import CompositionalUnit
        item = Score().add(CompositionalUnit.from_ut(
            TemporalUnit(span=1, tempus='4/4', prolatio=(1, 1, 2),
                         beat='1/4', bpm=60)), name='a')
        unit = item.unit
        assert unit.durations == pytest.approx((1.0, 1.0, 2.0))
        before = unit._rt._structure_version
        item.stretch(2.0)

        assert unit._rt._structure_version == before   # no node was touched
        assert unit._timing_dirty is True
        assert self._would_recompute(unit)
        assert unit.durations == pytest.approx((2.0, 2.0, 4.0))

    def test_the_diagram_draws_two_routes_from_clean_to_dirty(self):
        section = _lifecycle_section(8)
        diagram = section.split('```mermaid')[1].split('```')[0]
        assert diagram.count('Clean --> Dirty') == 2, (
            'one transition cannot show two independent staleness signals')
        assert '_timing_dirty' in diagram
        assert '_structure_version' in diagram

    def test_the_prose_names_both_halves_and_says_neither_suffices(self):
        section = _lifecycle_section(8)
        for token in ('_timing_dirty', '_timing_cache_version',
                      '_rt._structure_version', 'replace_node'):
            assert token in section, token
        squashed = _squash(section)
        assert 'either' in squashed.lower()
        assert 'offset-free' in squashed


# ---------------------------------------------------------------------------
# The relocation contract (b5be431). The tree stack gained a rule -- id-keyed
# state follows its content across a node-id change -- plus a public hook for
# registering an owner of such state. The architecture docs still described
# only the old half.
# ---------------------------------------------------------------------------

def _arch(name):
    """The full text of one file under ``docs/architecture/``."""
    return (REPO / 'docs' / 'architecture' / name).read_text()


def _arch_section(name, heading):
    """The body of one section of an architecture doc, heading excluded and
    whitespace collapsed. ``heading`` is the whole heading line
    (``'### Storage Model'``); the section ends at the next heading of the
    same or higher level. Scoping a text pin to its section keeps it from
    passing on a sentence that happens to sit somewhere else in the file;
    squashing keeps it from breaking when someone reflows a paragraph."""
    lines = _arch(name).split('\n')
    level = len(heading) - len(heading.lstrip('#'))
    starts = [i for i, line in enumerate(lines) if line.strip() == heading]
    assert len(starts) == 1, f'{heading!r} not found exactly once in {name}'
    body = []
    for line in lines[starts[0] + 1:]:
        if line.startswith('#') and len(line) - len(line.lstrip('#')) <= level:
            break
        body.append(line)
    return _squash('\n'.join(body))


def _mermaid_class_block(name, class_name):
    """The member lines of one ``class X { ... }`` block of a mermaid class
    diagram. Matched line-wise: ``class Tree {`` is a prefix of the
    inheritance-summary stub ``class Tree { topos }`` in the same file."""
    lines = _arch(name).split('\n')
    opener = f'class {class_name} {{'
    starts = [i for i, line in enumerate(lines) if line.strip() == opener]
    assert len(starts) == 1, f'{opener!r} not found exactly once in {name}'
    body = []
    for line in lines[starts[0] + 1:]:
        if line.strip() == '}':
            break
        body.append(line.strip())
    return body


class TestTheRelocationContractReachesTheArchitectureDocs:
    """Before this, 01_TOPOS.md told a reader that everything attached to a
    shifted sibling now names the wrong node -- which is the defect b5be431
    fixed -- and left clearing id-keyed state as an unowned obligation on
    "any code" that keeps some, so an agent following the doc hand-rolls a
    purge the layer already does. The docstrings had gained the missing half
    and the docs had not."""

    def test_topos_says_the_trees_own_state_is_not_an_external_handle(self):
        section = _arch_section('01_TOPOS.md', '### Child Order Is Node Index')
        assert 'is not an external handle' in section
        assert 'instrument bindings' in section

    def test_topos_names_both_seams_and_every_verb_that_removes_a_node(self):
        section = _arch_section('01_TOPOS.md',
                                '### Id-Keyed State Follows Content')
        assert 'on_structure_changed' in section        # the DEATH seam
        assert '_notify_nodes_relocated' in section     # the RELOCATION seam
        # backticked, so `prune` is not satisfied by `prune_leaves`
        for deleter in ('`prune`', '`remove_subtree`', '`prune_leaves`',
                        '`prune_to_depth`'):
            assert deleter in section, deleter
        for raiser in ('`Tree.insert_child`', '`RhythmTree._respell`',
                       '`subdivide`'):
            assert raiser in section, raiser

    def test_topos_states_the_totality_rule(self):
        """The mapping being total over survivors is the whole reason a
        receiver never has to ask whether an id still exists -- mid-respell
        it would get a lie."""
        section = _arch_section('01_TOPOS.md',
                                '### Id-Keyed State Follows Content')
        assert 'total over' in section
        assert 'destroyed' in section

    def test_the_tree_class_diagram_lists_the_public_observer_hook(self):
        assert '+set_id_state_observer(callback)' in _mermaid_class_block(
            '01_TOPOS.md', 'Tree')
        from klotho.topos.graphs.trees import Tree
        assert callable(getattr(Tree, 'set_id_state_observer', None))

    def test_topos_states_what_the_observer_does_not_cover(self):
        """The useful half is the negative one: a pure deletion raises no
        relocation, and a clone is not given the observer."""
        section = _arch_section('01_TOPOS.md',
                                '### Id-Keyed State Follows Content')
        assert 'A pure deletion' in section
        assert 'A clone gets no observer' in section

    def test_chronos_repeats_the_caveat_where_it_repeats_the_invariant(self):
        section = _arch_section('02_CHRONOS.md', '## Two Structural Invariants')
        assert 'is not an external handle' in section
        assert '_migrate_tie_to_first_child' in section

    def test_the_chronos_ties_section_states_the_fourth_rule(self):
        """Three rules were listed; the fourth is user-visible and was
        nowhere. Inserting into a tied leaf used to turn two attacks into
        three with nothing raised."""
        section = _arch_section('02_CHRONOS.md', '### 1.1 Ties')
        assert 'A fourth rule' in section
        assert '_migrate_tie_to_first_child' in section
        assert 'insert_child' in section and 'subdivide' in section

    def test_the_thetos_diagram_lists_the_relocation_handler(self):
        assert '+on_nodes_remapped(tree, mapping)' in _mermaid_class_block(
            '05_THETOS.md', 'ParameterLayer')
        from klotho.thetos.parameters.parameter_tree import ParameterLayer
        assert callable(getattr(ParameterLayer, 'on_nodes_remapped', None))

    def test_the_thetos_storage_model_says_bindings_are_purged_and_moved(self):
        section = _arch_section('05_THETOS.md', '### Storage Model')
        assert 'RT-28' in section
        assert 'on_nodes_remapped' in section
        assert 'in place' in section


class TestTheIdStateObserverContract:
    """``Tree.set_id_state_observer`` is public, is what an owner of
    id-keyed state living OUTSIDE the tree registers, and had no test of its
    own. These pin the three statements the architecture doc now makes about
    it -- including the two limits, which are the half a reader needs."""

    @staticmethod
    def _tree():
        """A base ``Tree``: the contract belongs to ``Tree``, and
        ``RhythmTree.subtree`` rebuilds from the S-form rather than copying,
        so it could not inherit an observer even if the copy paths leaked
        one."""
        from klotho.topos.graphs.trees import Tree
        return Tree(1, (1, 1, 1))

    def test_a_relocation_reaches_the_observer(self):
        """Rank-0 insert: each old child's content moves one slot right, so
        the mapping sends each old id to its right-hand neighbour."""
        tree = self._tree()
        seen = []
        tree.set_id_state_observer(seen.append)
        first, second, third = tree.leaf_nodes
        tree.insert_child(tree.root, 0, label=1)
        assert len(seen) == 1
        mapping = seen[0]
        assert mapping[first] == second
        assert mapping[second] == third
        assert mapping[tree.root] == tree.root

    def test_a_pure_deletion_raises_no_relocation(self):
        """Only layers get the DEATH seam. An owner outside the tree hears
        nothing from ``prune``/``remove_subtree`` and purges in its own
        deleter -- which is what ``CompositionalUnit.prune`` does."""
        for verb in ('prune', 'remove_subtree'):
            tree = self._tree()
            seen = []
            tree.set_id_state_observer(seen.append)
            getattr(tree, verb)(tree.leaf_nodes[-1])
            assert seen == [], verb

    @pytest.mark.parametrize('name, clone', [
        ('deepcopy', lambda t: __import__('copy').deepcopy(t)),
        ('structural_clone', lambda t: t.structural_clone()),
        ('subtree', lambda t: t.subtree(t.root)),
        ('from_tree_structure', lambda t: type(t).from_tree_structure(t)),
    ])
    def test_a_clone_carries_no_observer(self, name, clone):
        """A clone belongs to a different owner, which rebinds itself. If it
        inherited the observer, mutating the copy would heal the original's
        overlays against ids that never moved there."""
        tree = self._tree()
        seen = []
        tree.set_id_state_observer(seen.append)
        copied = clone(tree)
        copied.insert_child(copied.root, 0, label=1)
        assert seen == [], name


class TestTheGuardFileDescribesTheGuardItActuallyHas:
    """REC-1(b). RT-27 replaced the node-count guard with a structure-version
    guard and left the prose behind in the test file that exists to explain
    it. The code states the key in as many words -- ``temporal.py``: "Keyed
    on the TREE'S STRUCTURE VERSION, not on the node count." -- so the two
    can be compared without a human in the loop, which is the only reason
    this is testable at all."""

    @staticmethod
    def _guard_doc():
        path = Path(__file__).parent / 'test_perf_regression_guards.py'
        tree = ast.parse(path.read_text())
        node = next(
            n for n in tree.body
            if isinstance(n, ast.ClassDef)
            and n.name == 'TestTimingCacheInvalidationOnStructuralMutation')
        return ' '.join(ast.get_docstring(node).split())

    def test_it_does_not_claim_the_guard_counts_nodes(self):
        assert 'compares node' not in self._guard_doc(), (
            'the guard is keyed on the structure version, not the node count')

    def test_it_names_the_key_the_guard_actually_uses(self):
        assert 'structure version' in self._guard_doc().lower()


class TestThePreservedFamilyDoesNotDenyWhatItDoes:
    """``insert`` and ``scale`` both printed that control envelopes do NOT
    survive the rebuild. ``_respell`` -- three docstrings away in the same
    file -- says the source map carries "everything else keyed by node id
    (slurs, memoized Bind draws, control-envelope targets)", and
    ``tests/test_overlay_healing_matrix.py`` measures that it does. Two
    docstrings in one file contradicted each other and the behaviour
    settled it. This pins the prose to the measurement."""

    @staticmethod
    def _denials(method):
        return re.findall(r'[Cc]ontrol envelopes do\s+(?:not|NOT)',
                          inspect.getdoc(method) or '')

    def test_insert_does_not_claim_envelopes_are_lost(self):
        assert self._denials(RhythmTree.insert) == []

    def test_scale_does_not_claim_envelopes_are_lost(self):
        assert self._denials(RhythmTree.scale) == []

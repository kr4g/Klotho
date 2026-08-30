"""Regression pins for the W1 documentation wave.

A docstring cannot be tested directly, but the arithmetic and the absences it
asserts can be. These pin the claims that were wrong before the wave -- so if
the behaviour ever moves back, the wrong docstring is caught rather than
rediscovered by the next audit.
"""

from pathlib import Path

import pytest

import klotho.utils.playback as playback
from klotho.topos.graphs.lattices.lattices import Lattice
from klotho.topos.collections.sequences import Pattern
from klotho.thetos.instruments.synthdef import SynthDefInstrument

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

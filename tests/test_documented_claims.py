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


class TestStaleFileHeaders:
    """NEW-23. The headers named files that do not exist, which misdirects
    exactly the file:line citations an audit produces."""

    @pytest.mark.parametrize("rel", [
        'klotho/topos/collections/patterns.py',
        'klotho/chronos/rhythm_trees/algorithms.py',
        'klotho/chronos/rhythm_pairs/rhythm_pair.py',
        'klotho/chronos/temporal_units/temporal.py',
    ])
    def test_the_header_names_the_file_it_is_in(self, rel):
        head = (REPO / rel).read_text().split('\n')[:12]
        claimed = [line for line in head if 'klotho/' in line and line.lstrip().startswith('#')]
        assert claimed, f"{rel} lost its header"
        for line in claimed:
            assert rel in line, f"{rel} header claims: {line.strip()}"

    def test_no_file_in_the_package_claims_a_path_it_is_not(self):
        for path in (REPO / 'klotho').rglob('*.py'):
            rel = str(path.relative_to(REPO))
            for line in path.read_text().split('\n')[:12]:
                stripped = line.strip()
                if not stripped.startswith('#') or 'klotho/' not in stripped:
                    continue
                for token in stripped.split():
                    if token.endswith('.py') and 'klotho/' in token:
                        assert token.removeprefix('Klotho/') == rel, \
                            f"{rel} claims to be {token}"


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

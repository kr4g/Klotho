"""Klotho's output against Haddad's PRINTED figures -- the correctness oracle.

Everything else in this suite is a REGRESSION oracle. A golden captured from
Klotho's own output at some past moment proves that behaviour has not changed;
it cannot prove that behaviour is right, because both sides moved together when
it was captured. That distinction is why 7,000 green tests coexisted with 48
real defects.

The values here came from outside the codebase entirely: ``pdftotext`` over the
thesis Klotho claims to implement, captured by
``scripts/capture_haddad_figures.py`` into ``tests/fixtures/haddad_figures.json``.
No agent authored them and no Klotho code produced them, so when Klotho agrees
with one, that agreement means something.

WHAT THIS DOES NOT COVER. Nine figures, all from chapter 2. The operator
figures of section 4.5 carry their meaning in glyphs that pdftotext destroys --
those need image reading, and none of it is done here. Treat the count as the
honest size of the correctness surface, not as coverage.
"""
import json
import re
from pathlib import Path

import pytest

from klotho.chronos import RhythmTree as RT
from klotho.chronos.rhythm_trees.algorithms import evide
from klotho.topos.collections.patterns import autoref

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'haddad_figures.json'
FIGURES = json.loads(FIXTURE.read_text())['figures']


def _inner_tree(sexpr):
    """The rhythm tree inside Haddad's ``(? (((m n) ...)))`` wrapper."""
    m = re.search(r'\(\d+ \d+\)\s*\(', sexpr)
    i = m.end() - 1
    depth = 0
    for j in range(i, len(sexpr)):
        if sexpr[j] == '(':
            depth += 1
        elif sexpr[j] == ')':
            depth -= 1
            if depth == 0:
                return ' '.join(sexpr[i:j + 1].split())
    raise AssertionError(f'unbalanced s-expression: {sexpr!r}')


def _sexpr(node):
    """Render a Klotho S-form the way Haddad prints it (``1`` vs ``1.0``)."""
    if isinstance(node, float):
        return repr(node)
    if isinstance(node, int):
        return str(node)
    if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], tuple):
        return f'({_sexpr(node[0])} ({" ".join(_sexpr(x) for x in node[1])}))'
    return '(' + ' '.join(_sexpr(x) for x in node) + ')'


class TestTheFixtureIsTheThesisAndNotOurOwnOutput:
    """Guards on the oracle itself. If these fail, nothing below means anything."""

    def test_the_fixture_declares_where_its_values_came_from(self):
        meta = json.loads(FIXTURE.read_text())
        assert 'Haddad' in meta['source']
        assert 'pdftotext' in meta['provenance']
        assert 'not Klotho output' in meta['provenance']

    def test_figure_2_18_is_recorded_as_printed_unbalanced(self):
        """The thesis prints fig. 2.18 without its opening paren.

        A typo in the source, not in the extraction. Recorded rather than
        silently repaired, so nobody later "fixes" the fixture to match a
        cleaner reading and quietly loses the discrepancy.
        """
        assert FIGURES['2.18']['printed_unbalanced'] is True
        assert FIGURES['2.19'].get('printed_unbalanced') is False


class TestAutoreference:
    """Figs. 2.17-2.20: the seed (2 3) iterated three times."""

    SEED = (2, 3)

    @pytest.mark.parametrize('figure, depth', [('2.18', 1), ('2.19', 2), ('2.20', 3)])
    def test_klotho_reproduces_the_published_iteration(self, figure, depth):
        assert _sexpr(autoref(self.SEED, depth=depth)) == _inner_tree(FIGURES[figure]['sexpr'])


class TestEvide:
    """Fig. 2.14: le rythme evide ("the hollowed-out rhythm") of fig. 2.13.

    Haddad's term, from Boulez: the photographic negative of a rhythm, where
    sounding and silent are exchanged. Fig. 2.13 is evide's published input.
    """

    def test_klotho_reproduces_figure_2_14_from_figure_2_13(self):
        printed_2_13 = ((8, ((4, (-1, 1, 1, 1, 1)),
                             (2, (-1, 1, 1)),
                             (1, (-1, 1, 1, 1)),
                             (5, (-1, 1)),
                             (5, (-4, -1)),
                             (3, (-1, 1, 1, 1, 1)))),)
        got = evide(RT(meas='8/2', subdivisions=printed_2_13))
        # ``subdivisions`` is the whole group LIST, which is the level Haddad
        # prints inside his measure wrapper -- not its single element.
        assert _sexpr(got.subdivisions) == _inner_tree(FIGURES['2.14']['sexpr'])

"""What the Haddad operator family SAYS when it refuses (docket OPS-9/12/14).

Three defects in error surfaces. None of them changes what a correct call
computes; all three change what a wrong call is told, and one of them
routes the reader into silently wrong music.

- OPS-12: a runtime message quotes Haddad in French with no English
  translation, while its three siblings in the same module translate
  theirs inline. The project owner reads English only.
- OPS-14: four verbs never type-check their operand and leak raw
  ``AttributeError``s naming private internals, where five siblings in
  the same module give a shaped, redirecting ``TypeError``.
- OPS-9: ``scale``'s non-positive-ratio refusal names an index-addressed
  remedy and a NODE-addressed one in one sentence, so a caller holding a
  decomposed index who follows the second half edits the wrong event.
"""

import ast
import pathlib
import re

import pytest

from klotho.chronos import RhythmTree, TemporalUnit
import klotho.chronos.rhythm_trees.algorithms as ra
import klotho.chronos.temporal_units.algorithms as ta


# ------------------------------------------------------------------------------
# OPS-12 -- every French quotation in a runtime message carries its English
# ------------------------------------------------------------------------------

#: A closing guillemet, then the English gloss: whitespace and the joining
#: punctuation the module already uses (``(``, ``--``, an en/em dash), then
#: an ASCII double quote opening the translation.
_GLOSS_FOLLOWS = re.compile(r'»[\s(\-–—]*"')


def _raise_messages(module):
    """Every literal message text a ``raise`` in *module* can print.

    f-string placeholders come back as ``{}``: the interpolated value is
    never the part carrying a citation, and collapsing it lets the check
    read the surrounding prose as one string. Implicit concatenation is
    already one AST node, so a message split over six source lines is
    returned whole.
    """
    source = pathlib.Path(module.__file__).read_text(encoding='utf-8')
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise):
            continue
        inside_fstring = {
            id(part)
            for sub in ast.walk(node) if isinstance(sub, ast.JoinedStr)
            for part in ast.walk(sub) if part is not sub
        }
        for sub in ast.walk(node):
            if isinstance(sub, ast.JoinedStr):
                out.append((sub.lineno, ''.join(
                    v.value if isinstance(v, ast.Constant) else '{}'
                    for v in sub.values)))
            elif (isinstance(sub, ast.Constant)
                  and isinstance(sub.value, str)
                  and id(sub) not in inside_fstring):
                out.append((sub.lineno, sub.value))
    return out


class TestEveryRuntimeFrenchQuotationIsTranslated:
    """OPS-12 -- the standing rule, policed at the module rather than the line.

    The house pattern already exists three times over in this module; this
    pins it so a fourth untranslated quotation cannot ship.
    """

    def test_no_shipped_message_leaves_a_french_quotation_bare(self):
        offenders = [
            (line, text) for line, text in _raise_messages(ra)
            if '»' in text and not _GLOSS_FOLLOWS.search(text)
        ]
        assert offenders == [], (
            "these raise messages quote Haddad in French with no English "
            "translation immediately after the closing guillemet: "
            + '; '.join(f'{ra.__file__}:{line}' for line, _ in offenders)
        )

    def test_the_out_of_range_message_glosses_its_quotation(self):
        rt = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError) as excinfo:
            ra.diminish(rt, 9)
        msg = str(excinfo.value)
        assert 'position de tête de séquence' in msg
        assert 'head-of-sequence position' in msg

    def test_the_french_is_kept_because_it_is_the_citation(self):
        """The original is evidence -- a translation does not replace it."""
        rt = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError) as excinfo:
            ra.scale_tempus(rt, 2, 17)
        assert '«' in str(excinfo.value) and '»' in str(excinfo.value)

    @pytest.mark.parametrize('call', [
        lambda: ra.diminish(RhythmTree(meas='4/4', subdivisions=(1, 1)),
                            [0, 1]),
        lambda: ra.segment(RhythmTree(meas='4/4', subdivisions=(1, 1)), 2),
    ])
    def test_the_siblings_that_already_translated_still_do(self, call):
        with pytest.raises(ValueError) as excinfo:
            call()
        assert _GLOSS_FOLLOWS.search(str(excinfo.value))


# ------------------------------------------------------------------------------
# OPS-14 -- the operand guard is the family's, not five members' of it
# ------------------------------------------------------------------------------

def _ut():
    return TemporalUnit(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=60)


#: The nine RT-level verbs that take a tree, each called with a
#: TemporalUnit -- the wrong layer, and the mistake a composer actually
#: makes. Five of these were already shaped; four leaked.
RT_LEVEL_VERBS = [
    ('diminish', lambda: ra.diminish(_ut(), 0)),
    ('fuse', lambda: ra.fuse([_ut()])),
    ('segment', lambda: ra.segment(_ut(), '1/2')),
    ('scale_tempus', lambda: ra.scale_tempus(_ut(), 2, 0)),
    ('augment', lambda: ra.augment(_ut(), 1, 0)),
    ('decompose', lambda: ra.decompose(_ut())),
    ('flatten', lambda: ra.flatten(_ut())),
    ('filtrage', lambda: ra.filtrage(_ut(), (1, 2))),
    ('evide', lambda: ra.evide(_ut())),
]

#: Names a refusal must never print. Every one of these is a private
#: handle or an internal graph accessor; CLAUDE.md designates ``_rx`` as
#: unreachable from outside the class hierarchy in the first place.
LEAKED_INTERNALS = ('_rx', '_rt', 'leaf_nodes', 'descendants',
                    'object has no attribute')


class TestEveryRTLevelVerbRefusesTheWrongLayerByName:
    """OPS-14 -- nine verbs, one refusal shape."""

    @pytest.mark.parametrize('verb, call', RT_LEVEL_VERBS,
                             ids=[v for v, _ in RT_LEVEL_VERBS])
    def test_a_temporal_unit_gets_a_shaped_type_error(self, verb, call):
        with pytest.raises(TypeError) as excinfo:
            call()
        msg = str(excinfo.value)
        assert msg.startswith(verb), msg
        assert 'TemporalUnit' in msg, msg
        for leak in LEAKED_INTERNALS:
            assert leak not in msg, f'{verb} leaked {leak!r}: {msg}'

    @pytest.mark.parametrize('verb', ['filtrage', 'evide'])
    def test_the_two_with_no_tu_sibling_say_so_and_route_anyway(self, verb):
        """These cannot redirect to a TU-level twin -- there is none.

        Silence would be the easy answer; the message states the absence
        and names the public lift instead.
        """
        call = dict(RT_LEVEL_VERBS)[verb]
        with pytest.raises(TypeError) as excinfo:
            call()
        msg = str(excinfo.value)
        assert 'ut.rt' in msg, msg

    def test_the_tu_level_decompose_has_the_same_guard_as_its_neighbour(self):
        """``ta.flatten(None)`` was already shaped; ``ta.decompose`` was not."""
        with pytest.raises(TypeError) as excinfo:
            ta.decompose(None)
        msg = str(excinfo.value)
        assert msg.startswith('decompose'), msg
        assert 'NoneType' in msg, msg
        for leak in LEAKED_INTERNALS:
            assert leak not in msg, msg

    def test_the_guards_do_not_narrow_what_already_worked(self):
        rt = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))
        assert len(ra.decompose(rt)) == 4
        assert ra.flatten(rt).subdivisions == (1, 1, 1, 1)
        assert ra.filtrage(rt, (2,)).subdivisions == (-1, 1, -1, 1)
        assert ra.evide(rt).subdivisions == (-1, -1, -1, -1)
        assert len(ta.decompose(_ut())) == 2


# ------------------------------------------------------------------------------
# OPS-9 -- the two remedies do not take the same argument, and it says so
# ------------------------------------------------------------------------------

def _refusal():
    rt = RhythmTree(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
    with pytest.raises(ValueError) as excinfo:
        rt.scale(2, -1)
    return str(excinfo.value)


class TestScaleRefusalAddressesBothRemediesExplicitly:
    """OPS-9 -- following the old sentence rested the event one to the LEFT."""

    def test_the_message_marks_extract_as_index_addressed(self):
        msg = _refusal()
        assert 'extract' in msg
        head = msg[:msg.index('make_rest')]
        assert 'INDEX' in head or 'index' in head, msg

    def test_the_message_marks_make_rest_as_node_addressed(self):
        msg = _refusal()
        at = msg.index('make_rest')
        assert 'NODE' in msg[at:at + 120] or 'node' in msg[at:at + 120], msg

    def test_the_message_warns_that_an_index_passed_as_a_node_is_silent(self):
        msg = _refusal()
        assert 'silent' in msg.lower(), msg

    def test_the_message_gives_a_conversion_and_the_conversion_is_correct(self):
        """The recipe is asserted, then run: node ids of decomposed event i."""
        msg = _refusal()
        assert 'tie_groups' in msg, msg

        rt = RhythmTree(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        for node in rt.tie_groups[2]:
            rt.make_rest(node)
        assert rt.subdivisions == (4, 2, -3, 6, 3)

    def test_the_hazard_the_old_wording_walked_into(self):
        """``make_rest(2)`` on this tree rests the SECOND event, not the third."""
        rt = RhythmTree(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.make_rest(2)
        assert rt.subdivisions == (4, -2, 3, 6, 3)
        assert _refusal().count('make_rest') >= 1

    def test_the_ratio_docstring_no_longer_repeats_the_conflation(self):
        doc = RhythmTree.scale.__doc__
        at = doc.index('ratio : Fraction')
        block = doc[at:at + 900]
        assert 'make_rest' in block
        assert 'node' in block.lower(), block
        assert 'tie_groups' in block, block

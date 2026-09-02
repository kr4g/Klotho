"""AF-3.5 -- guards that keep the suite's own guards honest.

This project has now found seven checks that were green while guarding
nothing: an early return when two sides agreed, an empty loop with no "did
we check anything" assertion, a both-empty comparison, an ``is not None``
over a float64 column where a hole reads ``NaN``, a probe set containing
none of the inputs its test was named for, an ``or`` where ``and`` was
meant, and a replace-vs-merge test whose fixture made the two identical.
Two of them were written by agents who believed they were being careful.

The tests here are the ones that generalise -- the ones that catch the NEXT
instance rather than restating a fixed one:

1. **Citations resolve.** A mutation register that names code by line
   number rots silently; five of fourteen in one file had drifted onto
   unrelated lines. This asserts every register entry's quoted line really
   lives in the function it names.
2. **The known-vacuous shapes stay repaired.** Each repaired guard is
   re-stated here as a property of the guard itself, so deleting the repair
   is loud.
"""

import ast
import math
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
TESTS = REPO / 'tests'


# ---------------------------------------------------------------------------
# AUD-135 -- the mutation register cites code that exists, where it says
# ---------------------------------------------------------------------------

#: ``path :: ``func()`` — ... `quoted line` ...`` as rewritten for AUD-135.
_CITATION = re.compile(
    r'(klotho/[\w/]+\.py)\s*::\s*``(\w+)\(\)``\s*[—-]\s*(.*?)(?=\n\n|\Z)',
    re.S,
)

#: Files carrying a mutation register in this form.
_REGISTER_FILES = ['test_rt_operator_composition_laws.py']


def _function_bodies(path):
    """``{name: normalized source lines}`` for every def in *path*."""
    src = path.read_text()
    lines = src.splitlines()
    out = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = [' '.join(l.split())
                    for l in lines[node.lineno - 1:node.end_lineno]]
            out.setdefault(node.name, []).extend(body)
    return out


def _citations(name):
    text = (TESTS / name).read_text()
    return [(m.group(1), m.group(2), m.group(3))
            for m in _CITATION.finditer(text)]


@pytest.mark.parametrize('name', _REGISTER_FILES)
def test_the_mutation_register_cites_a_function_that_exists(name):
    """Every entry names a real function in a real module."""
    cites = _citations(name)
    # Without this the parametrization over a file whose register has been
    # deleted, or whose format has drifted out from under the regex, runs an
    # empty loop and passes unconditionally.
    assert len(cites) >= 10, (
        f'{name}: found {len(cites)} citations, expected the full register. '
        f'Either the register shrank or its format changed and this guard '
        f'stopped matching -- both are reasons to look, not to lower this '
        f'number')

    missing = []
    for path, func, _body in cites:
        src = REPO / path
        if not src.exists():
            missing.append(f'{path} does not exist')
        elif func not in _function_bodies(src):
            missing.append(f'{path} has no def {func}()')
    assert not missing, (
        f'{name}: the mutation register points at code that is not there:\n  '
        + '\n  '.join(missing))


@pytest.mark.parametrize('name', _REGISTER_FILES)
def test_every_cited_mutation_quotes_a_line_that_is_really_there(name):
    """The half a line number could never carry.

    A register entry is only usable if the line it tells you to change is
    findable. Each entry's FIRST backquoted snippet is matched against the
    body of the function it names -- so an edit that moves the code keeps
    the citation valid, and an edit that CHANGES the code invalidates it
    loudly, which is exactly when a mutation register has gone stale.
    """
    checked = 0
    unfound = []
    for path, func, body in _citations(name):
        quotes = re.findall(r'`([^`]+)`', body)
        if not quotes:
            unfound.append(f'{func}(): the entry quotes no code at all')
            continue
        wanted = ' '.join(quotes[0].split())
        if wanted.endswith('...'):        # an explicitly elided quote
            wanted = wanted[:-3].strip()
        bodies = _function_bodies(REPO / path).get(func, [])
        checked += 1
        if not any(wanted in line for line in bodies):
            unfound.append(
                f'{path} :: {func}() does not contain {wanted!r}')

    assert checked >= 10, (
        f'{name}: only {checked} entries carried a quotable line, so this '
        f'guard checked almost nothing')
    assert not unfound, (
        f'{name}: the register quotes code its function does not have -- the '
        f'mutation cannot be reproduced as written:\n  '
        + '\n  '.join(unfound))


# ---------------------------------------------------------------------------
# The repaired shapes, re-stated as properties of the guards themselves
# ---------------------------------------------------------------------------

def test_a_hole_in_an_events_column_reads_as_nan_and_never_as_none():
    """The premise behind the ``_holes`` helper in test_overlay_rebake_gate.

    If this ever stops being true -- if the column grows an object dtype, or
    a hole starts arriving as ``None`` -- then ``is not None`` becomes an
    adequate check again and the helper's docstring is wrong. Either way the
    next reader needs to be told, so it is asserted rather than assumed.
    """
    from klotho.thetos import CompositionalUnit as UC

    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
            pfields={'amp': 0.1})
    leaf = list(uc._rt.leaf_nodes)[1]
    uc.set_pfields(leaf, amp=None)

    column = list(uc.events['amp'])
    hole = column[1]
    assert isinstance(hole, float) and math.isnan(hole), (
        f'a missing amp no longer reads as NaN but as {hole!r}; '
        f'test_overlay_rebake_gate._holes needs revisiting')
    assert hole is not None, (
        'NaN is not None -- this is the whole trap, and if it ever stops '
        'holding, `is not None` becomes a valid emptiness check again')


def test_the_dynatos_converters_refuse_nan_rather_than_returning_it():
    """AF-3.5 shape (f): the probe set must contain the input it is named
    for. Stated here so the property survives any edit to that file."""
    from klotho.dynatos.dynamics import ampdb, dbamp

    for fn, label in ((ampdb, 'ampdb'), (dbamp, 'dbamp')):
        with pytest.raises(ValueError) as exc:
            fn(float('nan'))
        assert 'nan' in str(exc.value).lower(), (
            f'{label} refused NaN without naming it: {exc.value}')


def test_replace_node_replaces_rather_than_merging():
    """AF-3.5 shape (g), stated where the fixture cannot flatten it.

    ``test_parameter_tree_replace_node_updates_structure_and_data`` could not
    tell replace from merge because its target carried ``{}``. The
    distinguishing property is one line: a key the call never mentions must
    not survive it.
    """
    from klotho.thetos.parameters.parameter_tree import ParameterTree

    pt = ParameterTree(1, (11, 12, 13))
    node = [n for n in pt.nodes if pt.parent(n) == pt.root][0]
    pt.set_pfields(node, amp=0.5)
    assert dict(pt.nodes[node]) == {'amp': 0.5}, 'fixture did not take'

    pt.replace_node(node, pitch=64)

    assert dict(pt.nodes[node]) == {'pitch': 64}, (
        f'replace_node merged: {dict(pt.nodes[node])}. A REPLACE that keeps '
        f'the old keys is a merge under another name, and callers reading '
        f'the verb will be wrong about what survives')

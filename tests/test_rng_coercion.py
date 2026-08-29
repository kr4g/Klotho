"""One definition of ``_coerce_rng`` for every random draw in Klotho.

The helper that turns a caller's ``seed``/``rng`` argument into a random
source was copied into **five** modules across ``utils``, ``topos`` and
``tonos`` — three naming the parameter ``seed``, two naming it ``rng``.
Every call site passed positionally and all five bodies were measured
identical, so collapsing them to :mod:`klotho.utils._rng` changed no draw.

These tests exist because the risk that duplication carried was silent: one
copy drifting would have changed the draws in one subpackage only, with
nothing to catch it. The first test pins the count at one; the rest pin the
behaviour the single copy is now responsible for everywhere.
"""

import ast
import importlib
import pathlib
import random

import pytest

from klotho.utils._rng import _coerce_rng

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "klotho"

# The eight modules that reach the helper: five that once defined their own
# copy, plus three that imported one of those copies from a sibling.
CONSUMERS = [
    "klotho.utils.algorithms.graphs",
    "klotho.utils.algorithms.random",
    "klotho.topos.formal_grammars.rules",
    "klotho.topos.formal_grammars.rewriting",
    "klotho.topos.formal_grammars.derivation",
    "klotho.topos.formal_grammars.markov",
    "klotho.topos.graphs.lattices.algorithms",
    "klotho.tonos.tonality",
]


def _definition_sites():
    """Every module in the package that defines a ``_coerce_rng`` of its own."""
    sites = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_coerce_rng":
                sites.append(str(path.relative_to(PACKAGE_ROOT)))
    return sorted(sites)


def test_exactly_one_definition_in_the_package():
    assert _definition_sites() == ["utils/_rng.py"], (
        "_coerce_rng must be defined once, in klotho/utils/_rng.py; found: "
        + ", ".join(_definition_sites())
    )


@pytest.mark.parametrize("module_name", CONSUMERS)
def test_consumers_use_the_canonical_helper(module_name):
    module = importlib.import_module(module_name)
    assert module._coerce_rng.__module__ == "klotho.utils._rng"
    assert module._coerce_rng is _coerce_rng


def test_none_draws_from_the_global_stream():
    assert _coerce_rng(None) is random


def test_the_random_module_itself_passes_as_the_global_stream():
    assert _coerce_rng(random) is random


def test_a_random_instance_passes_through_unchanged():
    instance = random.Random(7)
    assert _coerce_rng(instance) is instance


@pytest.mark.parametrize("seed", [0, 1, 42, -3, 3.5, "abc", b"xy", bytearray(b"z")])
def test_a_seed_gives_the_same_draws_as_seeding_directly(seed):
    drawn = [_coerce_rng(seed).random() for _ in range(3)]
    expected = [random.Random(seed).random() for _ in range(3)]
    assert drawn == [expected[0]] * 3  # a fresh source each call
    assert _coerce_rng(seed).random() == expected[0]


@pytest.mark.parametrize("seed", [(1, 2), object()])
def test_an_unseedable_value_still_raises(seed):
    with pytest.raises(TypeError):
        _coerce_rng(seed)


def test_seeding_does_not_reseed_the_callers_global_stream():
    random.seed(12345)
    before = [random.random() for _ in range(3)]
    random.seed(12345)
    _coerce_rng(999).random()
    after = [random.random() for _ in range(3)]
    assert before == after

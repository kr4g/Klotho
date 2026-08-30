"""The suite polices its own oracles.

A test proves nothing if its EXPECTED value was produced by the code under
test. The failure is silent and total: the assertion passes for any behaviour,
including wrong behaviour, because both sides move together.

WHAT ACTUALLY PREVENTS THIS is the red-first discipline -- a test written from
the code's own output passes on its first run, so an agent required to WATCH IT
FAIL before implementing cannot produce one. This module guards the one hole
that discipline does not close: a checked-in golden file, which can be silently
REGENERATED from the working tree long after it was honestly captured.

Deliberately narrow. Self-comparison (``f(x) == f(x)``) is NOT flagged: it is
how determinism and purity are tested, it fools nobody, and flagging it buries
the real signal under false positives until someone deletes the check.
"""
import json
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent

GOLDEN = re.compile(r"(expected|golden|baseline|snapshot).*\.(json|txt|csv|xml)$", re.I)

# An oracle declares its provenance by naming, somewhere a reader will find it,
# the REFERENCE its values came from -- a published release, a separate
# worktree, a printed figure, a hand computation. Never the working tree.
_PROVENANCE = re.compile(
    r"origin/main|worktree|previous release|published|PyPI|"
    r"hand-?(computed|authored|written)|from the (figure|thesis|score)|"
    r"captured from|reference build",
    re.I,
)


def _declaring_texts(golden: Path):
    """Everything a reader would consult to learn where this oracle came from."""
    for cand in sorted(REPO.glob("scripts/*.py")) + sorted(TESTS.glob("*.py")) + \
                sorted(golden.parent.glob("README*")):
        try:
            text = cand.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if golden.name in text:
            yield cand, text


def test_every_checked_in_oracle_declares_where_its_values_came_from():
    """A golden with no stated provenance cannot later be distinguished from
    one regenerated out of the very code it is supposed to pin."""
    undeclared = []
    for g in sorted(TESTS.rglob("*")):
        if not g.is_file() or not GOLDEN.search(g.name):
            continue
        found = False
        for cand, text in _declaring_texts(g):
            if _PROVENANCE.search(text):
                found = True
                break
        if not found:
            undeclared.append(str(g.relative_to(REPO)))

    assert not undeclared, (
        "These oracle files declare no provenance.\n"
        "State, in the capture script or the test module that reads it, WHICH\n"
        "REFERENCE the baseline was taken from -- a published release, a\n"
        "separate worktree, a printed figure, a hand computation. Never the\n"
        "working tree, because a baseline captured from the working tree pins\n"
        "the code to itself and passes for any behaviour:\n  "
        + "\n  ".join(undeclared)
    )


def test_regenerable_oracles_say_what_regeneration_costs():
    """An oracle with a --regen switch is one command from being silenced.

    That is a legitimate design for a characterization test, but the switch
    must carry the warning next to it, or the next agent under pressure for a
    green suite will reach for it instead of fixing the defect it caught.
    """
    missing = []
    for t in sorted(TESTS.glob("test_*.py")):
        text = t.read_text(encoding="utf-8", errors="replace")
        if "--regen" not in text:
            continue
        # The warning must be present and must say the diff has to be reviewed.
        if not re.search(r"eyeball|review|inspect|verify", text, re.I):
            missing.append(str(t.relative_to(REPO)))

    assert not missing, (
        "These modules can regenerate their own oracle but never say that the\n"
        "regenerated diff must be reviewed by a human. Regenerating to make a\n"
        "red test green destroys the oracle:\n  " + "\n  ".join(missing)
    )

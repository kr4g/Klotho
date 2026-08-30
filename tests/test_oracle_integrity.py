"""A documentation lint over the suite's oracles. It reads text, not values.

A test proves nothing if its EXPECTED value was produced by the code under
test. The failure is silent and total: the assertion passes for any behaviour,
including wrong behaviour, because both sides move together.

WHAT ACTUALLY PREVENTS THIS is the red-first discipline -- a test written from
the code's own output passes on its first run, so an agent required to WATCH IT
FAIL before implementing cannot produce one.

WHAT THIS MODULE DOES NOT DO -- read this before trusting it.

It cannot tell an honest golden from a poisoned or a regenerated one. Nothing
here opens a golden file or compares a value; the checks match patterns against
filenames and against prose. Both holes below were measured against this tree
on 2026-08-29:

  * Sabotage. Edit klotho/utils/playback/supersonic/converters.py so every
    event starts 0.5s late, then run the documented
    ``python tests/test_lowering_equivalence.py --regen``. The whole suite goes
    green -- this module included -- with the sabotage still in the file. The
    golden had caught it one command earlier.
  * Poison. Multiply every number in
    tests/fixtures/lowering_equivalence_golden.json by 3 and add 1, leaving the
    code alone. Every check in this module still passes. Only the golden's own
    test fails.

A third hole is narrower but worth knowing: the provenance check is satisfied
by a provenance-ish WORD anywhere in a file that names the golden, so one
unrelated sentence containing "published" silences it for that file, forever.

WHAT IT IS, then, is two rules about what a reader can find out:

  1. Every checked-in golden must have, in a TRACKED file, a sentence saying
     which REFERENCE its values came from. Untracked does not count -- a
     declaration in a gitignored file is absent from a clone, so the check
     passes for its author and fails for everyone else. This repo shipped that
     exact failure: the only declaration for tests/expected_trees.json lived in
     gitignored scripts/, and a fresh clone failed this module on its own
     baseline. The declaration now lives in tests/conftest.py.
  2. A file that can rewrite a golden must say, next to the switch, that the
     regenerated diff has to be reviewed by a human.

Neither rule stops a regeneration. What limits the damage is the convention
stated in tests/test_lowering_equivalence.py: a regenerated golden is committed
ALONE, so its diff stays reviewable in isolation. Closing the hole itself needs
something this module is not -- a recorded fingerprint of each golden, checked
against the commit that last changed it.

Deliberately narrow. Self-comparison (``f(x) == f(x)``) is NOT flagged: it is
how determinism and purity are tested, it fools nobody, and flagging it buries
the real signal under false positives until someone deletes the check.
"""
import os
import re
import subprocess
from pathlib import Path
from unittest import mock

import pytest

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent

SELF = Path(__file__).resolve()

# Wide on purpose. A golden that this pattern misses is not reported as
# suspicious -- it is not reported at all, and the run looks clean.
GOLDEN = re.compile(
    r"(expected|golden|baseline|snapshot|reference|fixture|oracle)"
    r".*\.(json|txt|csv|xml|yaml|yml|pkl|npz|ndjson)$",
    re.I,
)

# An oracle declares its provenance by naming, somewhere a reader will find it,
# the REFERENCE its values came from -- a published release, a separate
# worktree, a printed figure, a hand computation. Never the working tree.
_PROVENANCE = re.compile(
    r"origin/main|worktree|previous release|published|PyPI|"
    r"hand-?(computed|authored|written)|from the (figure|thesis|score)|"
    r"captured from|reference build",
    re.I,
)

# The warning a regeneration switch must carry: the diff has to be looked at.
_REVIEW = re.compile(r"eyeball|review|inspect|verify", re.I)

_UNSET = object()


def _tracked_paths(repo):
    """Repo-relative paths git reports as tracked, or None when tracked-ness
    cannot be determined here.

    None means "accept every candidate". It is returned when git is missing,
    when ``repo`` is not the root of a checkout, or when the command fails --
    cases where what is on disk is all anyone can know about what a reader got.
    """
    repo = Path(repo)
    try:
        top = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=60,
        )
        if top.returncode != 0:
            return None
        if Path(top.stdout.strip()).resolve() != repo.resolve():
            return None
        listed = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z"],
            capture_output=True, text=True, timeout=120,
        )
        if listed.returncode != 0:
            return None
    except (OSError, subprocess.SubprocessError):
        return None
    return frozenset(p for p in listed.stdout.split("\0") if p)


def _declaring_texts(golden, repo=None, tests=None, tracked=_UNSET):
    """Everything a reader who cloned this repo would consult to learn where
    this oracle came from.

    Untracked candidates are skipped: they are not in a clone, so a
    declaration that lives only in one is a declaration only its author can
    read. This module is skipped too -- it quotes golden filenames and
    provenance words while discussing them, and would otherwise vouch for
    oracles it knows nothing about.
    """
    repo = REPO if repo is None else repo
    tests = TESTS if tests is None else tests
    if tracked is _UNSET:
        tracked = _tracked_paths(repo)
    for cand in sorted(repo.glob("scripts/*.py")) + sorted(tests.glob("*.py")) + \
                sorted(golden.parent.glob("README*")):
        if cand.resolve() == SELF:
            continue
        if tracked is not None:
            try:
                rel = cand.resolve().relative_to(Path(repo).resolve()).as_posix()
            except ValueError:
                rel = None  # outside the repo: tracked-ness says nothing
            if rel is not None and rel not in tracked:
                continue
        try:
            text = cand.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if golden.name in text:
            yield cand, text


def _undeclared_oracles(repo=None, tests=None):
    """Repo-relative paths of every golden with no provenance statement."""
    repo = REPO if repo is None else repo
    tests = TESTS if tests is None else tests
    tracked = _tracked_paths(repo)
    undeclared = []
    for g in sorted(tests.rglob("*")):
        if not g.is_file() or not GOLDEN.search(g.name):
            continue
        found = False
        for cand, text in _declaring_texts(g, repo=repo, tests=tests, tracked=tracked):
            if _PROVENANCE.search(text):
                found = True
                break
        if not found:
            undeclared.append(str(g.relative_to(repo)))
    return undeclared


def _regen_scan_paths(repo=None, tests=None):
    """Every file that could carry a regeneration switch.

    scripts/ is included although it is gitignored here. That cuts the wrong
    way on purpose: an untracked file can only ADD findings for whoever has it,
    never remove one from a clone, so the check stays at least as strict for a
    reader as it is for the author. The opposite arrangement -- an untracked
    file making a check PASS -- is the bug this module shipped with.
    """
    repo = REPO if repo is None else repo
    tests = TESTS if tests is None else tests
    return sorted(tests.glob("test_*.py")) + sorted(repo.glob("scripts/*.py"))


def _regen_offenders(paths, repo=None):
    """Repo-relative paths that can regenerate an oracle without saying so."""
    repo = REPO if repo is None else repo
    missing = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "--regen" not in text:
            continue
        # The warning must be present and must say the diff has to be reviewed.
        if not _REVIEW.search(text):
            missing.append(str(p.relative_to(repo)))
    return sorted(missing)


def test_every_checked_in_oracle_declares_where_its_values_came_from():
    """A golden with no stated provenance cannot later be distinguished from
    one regenerated out of the very code it is supposed to pin."""
    undeclared = _undeclared_oracles()

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
    missing = _regen_offenders(_regen_scan_paths())

    assert not missing, (
        "These modules can regenerate their own oracle but never say that the\n"
        "regenerated diff must be reviewed by a human. Regenerating to make a\n"
        "red test green destroys the oracle:\n  " + "\n  ".join(missing)
    )


# ---------------------------------------------------------------------------
# The guard's own guard.
#
# Both checks above are pattern matches over filenames and file text, so their
# holes are invisible from inside the repo: a golden the pattern does not match
# simply never appears in the report. These exercise the helpers against
# synthetic trees, where the right answer is known in advance.
# ---------------------------------------------------------------------------


def _synthetic_tree(root):
    """A miniature repo: goldens under tests/, capture scripts under scripts/."""
    (root / "tests").mkdir()
    (root / "scripts").mkdir()
    return root, root / "tests"


def _stage_in_new_git_repo(repo, tracked):
    """Make ``repo`` a git checkout whose index holds exactly ``tracked``.

    The paths are staged, not committed: ``git ls-files`` reports the index, so
    no commit -- and no user-identity configuration -- is needed.
    """
    try:
        subprocess.run(["git", "init", "-q", str(repo)],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "add", "-f", "--"] + list(tracked),
                       check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover
        pytest.skip(f"git is not usable here: {exc}")


def test_a_golden_stays_visible_when_renamed_or_stored_in_another_format(tmp_path):
    """A golden that the GOLDEN pattern misses is not reported as undeclared --
    it is not reported at all, which reads exactly like a clean run."""
    repo, tests = _synthetic_tree(tmp_path)
    names = [
        "expected_widget_layout.json",
        "expected_widget_layout.yaml",
        "golden_widget_metrics.yml",
        "baseline_widget_metrics.pkl",
        "snapshot_widget_metrics.npz",
        "reference_widget_events.ndjson",
        "fixture_widget_events.json",
        "oracle_widget_events.txt",
    ]
    for n in names:
        (tests / n).write_text("{}\n", encoding="utf-8")

    assert _undeclared_oracles(repo=repo, tests=tests) == sorted(
        f"tests/{n}" for n in names
    )


def test_a_provenance_statement_in_an_untracked_file_does_not_count(tmp_path):
    """A declaration that is not in git is absent from a fresh clone, so it
    makes the check pass here and fail for everyone else. That is the failure
    mode this repo actually shipped: see tests/conftest.py."""
    repo, tests = _synthetic_tree(tmp_path)
    (tests / "expected_tracked_case.json").write_text("{}\n", encoding="utf-8")
    (tests / "expected_untracked_case.json").write_text("{}\n", encoding="utf-8")
    (tests / "declares_tracked_case.py").write_text(
        "# expected_tracked_case.json was captured from a worktree checked out\n"
        "# to origin/main.\n", encoding="utf-8")
    (repo / "scripts" / "declares_untracked_case.py").write_text(
        "# expected_untracked_case.json was captured from a worktree checked\n"
        "# out to origin/main.\n", encoding="utf-8")
    _stage_in_new_git_repo(repo, [
        "tests/expected_tracked_case.json",
        "tests/expected_untracked_case.json",
        "tests/declares_tracked_case.py",
    ])

    assert _undeclared_oracles(repo=repo, tests=tests) == [
        "tests/expected_untracked_case.json"
    ]


def test_the_regeneration_warning_check_reaches_capture_scripts(tmp_path):
    """Regeneration lives in scripts/ as often as in tests/."""
    repo, tests = _synthetic_tree(tmp_path)
    silent = 'import sys\nif "--regen" in sys.argv:\n    rewrite_the_golden()\n'
    (tests / "test_silent_probe.py").write_text(silent, encoding="utf-8")
    (repo / "scripts" / "silent_probe.py").write_text(silent, encoding="utf-8")
    (repo / "scripts" / "loud_probe.py").write_text(
        'import sys\n'
        '# Regenerating discards the oracle: review the diff line by line.\n'
        'if "--regen" in sys.argv:\n    rewrite_the_golden()\n', encoding="utf-8")

    offenders = _regen_offenders(_regen_scan_paths(repo=repo, tests=tests), repo=repo)

    assert offenders == ["scripts/silent_probe.py", "tests/test_silent_probe.py"]


# ---------------------------------------------------------------------------
# The regeneration lock.
#
# Filed after a hostile pass proved the hole was open: sabotage the lowering
# pipeline, run the documented ``--regen``, re-run the suite, and everything is
# green with the sabotage still in the file. The oracle had been laundered out
# of the code it was supposed to be independent of.
#
# The capture scripts already SAY the right thing -- "capture from REMOTE
# klotho", "Do NOT run in main workspace". Nothing enforced it. These tests are
# the enforcement: every path that can overwrite an oracle must route through
# ``tests/_oracle_lock.require_regen_authorization``, which refuses unless a
# human set KLOTHO_ALLOW_REGEN=1.
# ---------------------------------------------------------------------------

_ORACLE_WRITERS = (
    TESTS / 'test_lowering_equivalence.py',
    REPO / 'scripts' / 'capture_expected_trees.py',
    REPO / 'scripts' / 'capture_expected_uc_pt.py',
    REPO / 'scripts' / 'capture_parity_fixtures.py',
)


def _regen_paths():
    """Every file in the repo that can overwrite a checked-in oracle.

    Found by scanning rather than listed, so a NEW capture script cannot slip
    in unguarded -- which is the failure mode this whole module exists for.
    """
    found = []
    for d in (TESTS, REPO / 'scripts'):
        if not d.is_dir():
            continue
        for p in sorted(d.glob('*.py')):
            text = p.read_text(encoding='utf-8', errors='replace')
            writes_oracle = (
                '--regen' in text
                or ('json.dump' in text and 'capture' in p.name)
            )
            if writes_oracle:
                found.append(p)
    return found


def test_every_oracle_regeneration_path_is_locked():
    """A path that can overwrite an oracle must ask the lock first.

    This is the guard the project did not have. Without it, an agent that
    implements a feature can regenerate the oracle that feature is tested
    against, from the feature's own output, and the suite goes green.
    """
    unguarded = [
        str(p.relative_to(REPO))
        for p in _regen_paths()
        if 'require_regen_authorization' not in p.read_text(encoding='utf-8', errors='replace')
    ]
    assert unguarded == [], (
        'these can overwrite a checked-in oracle without human authorization:\n  '
        + '\n  '.join(unguarded)
        + '\nEach must call tests/_oracle_lock.require_regen_authorization().'
    )


def test_the_lock_actually_refuses_when_unauthorized():
    """The lock must go red in both directions, or it is decoration."""
    import importlib
    lock = importlib.import_module('_oracle_lock')
    env = dict(os.environ)
    env.pop('KLOTHO_ALLOW_REGEN', None)
    with mock.patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit):
            lock.require_regen_authorization('tests/fixtures/whatever.json')
    with mock.patch.dict(os.environ, {**env, 'KLOTHO_ALLOW_REGEN': '1'}, clear=True):
        lock.require_regen_authorization('tests/fixtures/whatever.json')  # must not raise

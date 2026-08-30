"""Shared loaders for the suite's checked-in baselines.

PROVENANCE OF tests/expected_trees.json -- read before regenerating it.

The file was added in commit d756b39 (2026-02-28, version 4.5.2). Its values
were produced by scripts/capture_expected_trees.py, whose stated procedure is
to run it from a separate worktree checked out to origin/main, against that
remote code -- never against the working tree. Nothing enforces that; the
script only says it.

That capture script is NOT tracked (scripts/ is gitignored), so a clone of this
repo has the baseline and no way to re-run the capture. This paragraph is
therefore the whole surviving account of where these numbers came from, which
is why it lives here in a tracked file instead of next to the script.

Regenerating the file from the working tree would pin the code to itself: every
test that reads it would then pass for any behaviour, including the behaviour
it was written to catch. If it must be recaptured, capture from a worktree at
the last released tag, review the diff line by line, and commit the result
ALONE so that diff stays readable in isolation.
"""
import json
import os

_EXPECTED_TREES = None


def get_expected_trees():
    global _EXPECTED_TREES
    if _EXPECTED_TREES is None:
        path = os.path.join(os.path.dirname(__file__), "expected_trees.json")
        with open(path) as f:
            _EXPECTED_TREES = json.load(f)
    return _EXPECTED_TREES

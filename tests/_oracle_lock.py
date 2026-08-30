"""The lock on every path that can overwrite a checked-in test oracle.

WHY THIS EXISTS. A test proves nothing if its expected value was produced by
the code under test. The failure is silent and total: the assertion passes for
any behaviour, wrong included, because both sides moved together.

That hole was open in this repo and was measured on 2026-08-29 -- sabotage the
lowering pipeline so every event starts half a second late, run the documented
``python tests/test_lowering_equivalence.py --regen``, and the whole suite goes
green with the sabotage still in the file. The golden had caught it one command
earlier. Regeneration destroyed the only thing that could see the bug.

WHY A LOCK AND NOT A RULE. The rule already existed. Every capture script in
this repo opens by saying to run it against remote code only -- "Do NOT run in
main workspace", "capture from REMOTE klotho". The instructions were correct,
prominent, and unenforced, so they were followed exactly as long as whoever ran
the script happened to read them. This module is the same instruction expressed
as a refusal.

WHAT IT DOES NOT DO. It cannot tell an honest regeneration from a dishonest
one, and it cannot judge whether the values written are right. It does one
thing: it stops an oracle being overwritten by anything other than a deliberate
human act. Everything after that -- committing the golden ALONE so its diff is
reviewable, and actually reading that diff -- is still a person's job.
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Set this to ``1`` to authorize one regeneration run. Deliberately awkward:
#: it is meant to be typed by a person who has decided to do this, and it is
#: not the kind of thing that ends up in a script by accident.
ENV = 'KLOTHO_ALLOW_REGEN'

_REFUSAL = """\
REFUSED: regenerating {target} would overwrite a test oracle.

An oracle regenerated from the working tree is no longer independent of the
code it checks, and every test that reads it silently stops being able to fail.
This is not hypothetical -- it was measured against this repo on 2026-08-29.

If you are a person who has decided to do this deliberately:

    {env}=1 {cmd}

Then commit the regenerated golden ALONE, in its own commit, so the diff is
reviewable in isolation -- and read that diff before you push it.

If you are an agent: you may not authorize this. Ask.
"""

_NOT_REMOTE = """\
REFUSED: {target} must be captured from a REFERENCE build, not this tree.

``klotho`` imported from {found}, which is inside the repository under test.
A baseline captured from the code it is supposed to check is not a baseline.

Capture it from a worktree checked out to the published release:

    git worktree add .worktree-remote origin/main
    PYTHONPATH=.worktree-remote {cmd}
"""


def require_regen_authorization(target, *, must_import_remote=False):
    """Refuse to overwrite ``target`` unless a human authorized this run.

    Parameters
    ----------
    target :
        The oracle path about to be written. Named in the refusal so the
        message says what was at stake.
    must_import_remote :
        When True, additionally refuse if ``klotho`` resolved to this
        repository. Capture scripts set this: their whole contract is that the
        baseline comes from a reference build, and until now that contract was
        prose in a docstring.

    Raises
    ------
    SystemExit
        With an explanation. Never a bare exit code -- a refusal nobody can
        read is how a guard gets deleted rather than satisfied.
    """
    cmd = ' '.join([Path(sys.executable).name, *sys.argv]) if sys.argv else 'the capture script'

    if os.environ.get(ENV) != '1':
        raise SystemExit(_REFUSAL.format(target=target, env=ENV, cmd=cmd))

    if must_import_remote:
        try:
            import klotho
        except ImportError:
            return
        found = Path(klotho.__file__).resolve()
        if REPO in found.parents:
            raise SystemExit(_NOT_REMOTE.format(target=target, found=found, cmd=cmd))

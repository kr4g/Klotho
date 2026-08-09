"""Finish timing: a piece is over at its musical end PLUS the trailing
pause (V5).

The V4 core computed ``pieceDur = basePieceDur + tailPause`` in play() and
then never used it: both finish arms fired at the base duration, so every
shape widget (default pause=0.25) reset its visuals early by exactly the
pause. Behavioral probe runs the real scheduler_core.js under Node with a
virtual clock (see ``fixtures/finish_timing_probe.mjs``).
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROBE = Path(__file__).parent / "fixtures" / "finish_timing_probe.mjs"


def _run(case):
    proc = subprocess.run(["node", str(PROBE), case],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
class TestFinishTiming:
    # All times: STARTUP_DELAY (0.1 s) + base piece duration (2.0 s)
    # + trailing pause, on a virtual clock (sub-ms double rounding only;
    # the V4 bug was off by the full pause, >= 250 ms).

    def test_finish_without_pause_at_musical_end(self):
        assert _run("pause0")["finishAtMs"] == pytest.approx(2100, abs=0.01)

    def test_finish_includes_trailing_pause(self):
        assert _run("pause1")["finishAtMs"] == pytest.approx(3100, abs=0.01)

    def test_final_finite_loop_cycle_includes_trailing_pause(self):
        # Two cycles: between-cycle spacing (base 2 + pause 1) was already
        # correct in V4; the last cycle's END must add the pause too.
        assert _run("loop2-pause1")["finishAtMs"] == pytest.approx(6100, abs=0.01)

"""An event routed to a track that does not exist (charter NEW-19).

The scheduler resolves a track as ``trackMap[group] -> default -> main``, so a
typo in a group name plays on the main chain with none of the inserts that
were asked for, and nothing anywhere says so. The scheduler is JavaScript and
nothing bridges its console output back to Python, so the check that a
notebook user can actually see has to happen on the Python side.

Not an error: a misrouted score still plays. Turning it into a hard failure
would break working-but-wrong sessions, which is more than the charter asked.
"""

import pytest

from klotho.utils.playback import _sc_validate
from klotho.utils.playback._sc_validate import warn_unknown_event_groups


@pytest.fixture(autouse=True)
def _clean_dedupe():
    _sc_validate._WARNED_UNKNOWN_TRACKS.clear()
    yield
    _sc_validate._WARNED_UNKNOWN_TRACKS.clear()


def _events(*groups):
    return [{"type": "new", "id": f"e{i}", "group": g}
            for i, g in enumerate(groups)]


class TestWarnUnknownEventGroups:
    def test_an_unknown_group_is_reported(self, capsys):
        warn_unknown_event_groups(_events('sollo'), {'groups': ['solo']})
        assert "no track named 'sollo'" in capsys.readouterr().out

    def test_the_message_lists_the_tracks_that_do_exist(self, capsys):
        warn_unknown_event_groups(_events('sollo'), {'groups': ['solo', 'pads']})
        out = capsys.readouterr().out
        assert 'solo' in out and 'pads' in out

    def test_a_configured_track_is_silent(self, capsys):
        warn_unknown_event_groups(_events('solo'), {'groups': ['solo']})
        assert capsys.readouterr().out == ''

    def test_the_implicit_tracks_are_silent(self, capsys):
        warn_unknown_event_groups(_events('default', 'main'), {'groups': []})
        assert capsys.readouterr().out == ''

    def test_an_event_with_no_group_is_silent(self, capsys):
        warn_unknown_event_groups([{"type": "new", "id": "e0"}], {'groups': []})
        assert capsys.readouterr().out == ''

    def test_it_warns_once_per_name_not_once_per_event(self, capsys):
        warn_unknown_event_groups(_events('sollo', 'sollo', 'sollo'),
                                  {'groups': ['solo']})
        assert capsys.readouterr().out.count('no track named') == 1

    def test_two_different_typos_both_report(self, capsys):
        warn_unknown_event_groups(_events('sollo', 'padz'), {'groups': ['solo']})
        out = capsys.readouterr().out
        assert "'sollo'" in out and "'padz'" in out

    def test_a_missing_groups_key_still_permits_the_implicit_tracks(self, capsys):
        warn_unknown_event_groups(_events('main'), {})
        assert capsys.readouterr().out == ''

    def test_a_non_dict_meta_is_ignored(self, capsys):
        warn_unknown_event_groups(_events('sollo'), None)
        assert capsys.readouterr().out == ''

    def test_it_never_raises(self):
        warn_unknown_event_groups(_events('sollo'), {'groups': ['solo']})


class TestTheSchedulerFallbackNoLongerReachesForMain:
    """The JS half. ``setupTracks`` always aliases ``default`` to ``main``
    before publishing ``_trackMap``, so the third step of the old
    ``group -> default -> main`` chain was unreachable."""

    @staticmethod
    def _source():
        from pathlib import Path
        import klotho.utils.playback.supersonic as ss
        return (Path(ss.__file__).parent / 'scheduler_core.js').read_text()

    def test_the_dead_third_fallback_is_gone(self):
        assert 'this._trackMap["default"] || this._trackMap["main"]' not in self._source()

    def test_both_bundling_paths_warn(self):
        assert self._source().count('__klothoTrackWarned') >= 4

    def test_the_warning_dedupe_resets_when_the_track_map_does(self):
        src = self._source()
        assert src.count('globalThis.__klothoTrackWarned = {};') >= 3

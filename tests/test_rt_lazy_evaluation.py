from klotho.chronos import TemporalUnit as UT
from klotho.thetos import CompositionalUnit as UC


def test_temporal_unit_rt_does_not_force_evaluation():
    ut = UT(tempus="4/4", prolatio=(1,))
    assert not hasattr(ut, "_events")
    _ = ut.rt
    assert not hasattr(ut, "_events")


def test_compositional_unit_rt_does_not_force_evaluation():
    uc = UC(tempus="4/4", prolatio=(1,))
    assert not hasattr(uc, "_events")
    _ = uc.rt
    assert not hasattr(uc, "_events")


def test_temporal_unit_onsets_and_durations_evaluate_lazily():
    ut = UT(tempus="4/4", prolatio=(1,))
    assert not hasattr(ut, "_events")
    assert tuple(float(v) for v in ut.onsets) == (0.0,)
    assert tuple(float(v) for v in ut.durations) == (4.0,)


def test_temporal_unit_onsets_and_durations_do_not_materialize_events():
    ut = UT(tempus="4/4", prolatio=(1,))
    assert not hasattr(ut, "_events")
    _ = ut.onsets
    assert not hasattr(ut, "_events")
    _ = ut.durations
    assert not hasattr(ut, "_events")


def test_temporal_unit_len_does_not_force_evaluation():
    ut = UT(tempus="4/4", prolatio=(1,))
    assert not hasattr(ut, "_events")
    assert len(ut) == 1
    assert not hasattr(ut, "_events")


def test_compositional_unit_len_does_not_force_evaluation():
    uc = UC(tempus="4/4", prolatio=(1,))
    assert not hasattr(uc, "_events")
    assert len(uc) == 1
    assert not hasattr(uc, "_events")


def test_compositional_unit_pt_snapshot_does_not_materialize_events():
    uc = UC(tempus="4/4", prolatio=(1,))
    assert not hasattr(uc, "_events")
    _ = uc.pt
    assert not hasattr(uc, "_events")

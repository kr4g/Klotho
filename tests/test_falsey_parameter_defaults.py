import pytest

from klotho.thetos import CompositionalUnit as UC


@pytest.mark.parametrize("value", [0, False, [], (), ""])
def test_compositional_unit_get_pfield_preserves_falsey_values(value):
    uc = UC(tempus="4/4", prolatio=(1,))
    uc.set_pfields(uc._pt.root, freq=value)

    fallback = "fallback"
    assert uc.get_pfield(uc._rt.leaf_nodes[0], "freq", fallback) == value


@pytest.mark.parametrize("value", [0, False, [], (), ""])
def test_parametron_get_pfield_preserves_falsey_values(value):
    uc = UC(tempus="4/4", prolatio=(1,))
    uc.set_pfields(uc._pt.root, freq=value)

    event = next(iter(uc))
    fallback = "fallback"
    assert event.get_pfield("freq", fallback) == value


@pytest.mark.parametrize("value", [0, False, [], (), ""])
def test_compositional_unit_get_mfield_preserves_falsey_values(value):
    uc = UC(tempus="4/4", prolatio=(1,))
    uc.set_mfields(uc._pt.root, marker=value)

    fallback = "fallback"
    assert uc.get_mfield(uc._rt.leaf_nodes[0], "marker", fallback) == value


@pytest.mark.parametrize("value", [0, False, [], (), ""])
def test_parametron_get_mfield_preserves_falsey_values(value):
    uc = UC(tempus="4/4", prolatio=(1,))
    uc.set_mfields(uc._pt.root, marker=value)

    event = next(iter(uc))
    fallback = "fallback"
    assert event.get_mfield("marker", fallback) == value


@pytest.mark.parametrize("value", [0, False, [], (), ""])
def test_parameter_node_get_preserves_falsey_values(value):
    uc = UC(tempus="4/4", prolatio=(1,))
    uc.set_pfields(uc._pt.root, freq=value)

    fallback = "fallback"
    node = uc._rt.leaf_nodes[0]
    assert uc._pt[node].get("freq", fallback) == value


def test_set_pfields_invalidates_uc_event_cache():
    uc = UC(tempus="4/4", prolatio=(1,))
    first = list(uc)
    assert first[0].get_pfield("freq", None) is None

    uc.set_pfields(uc._pt.root, freq=220)
    second = list(uc)
    assert second[0].get_pfield("freq") == 220


def test_set_mfields_invalidates_uc_event_cache():
    uc = UC(tempus="4/4", prolatio=(1,))
    first = list(uc)
    assert first[0].get_mfield("marker", None) is None

    uc.set_mfields(uc._pt.root, marker=0)
    second = list(uc)
    assert second[0].get_mfield("marker") == 0

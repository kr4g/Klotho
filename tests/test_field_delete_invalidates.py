"""A field DELETE must invalidate what a field WRITE invalidates.

``ParameterLayer.remove_fields`` was the one field-write path in the layer
that reached into ``tree._rx[node]`` directly instead of going through
``_write_node_data``. Every other write bumps the tree's structure version on
the way past; a delete bumped nothing, so every consumer memoized on that
version went on serving values for a field that no longer exists.

This is EVENTS-1's second half, and the docket row's own sentence about the
first half -- "playback stays correct and only inspection lies" -- is FALSE
here. The staleness reaches the effective-parameter-tree snapshot that feeds
lowering, so ``remove_envelope`` left the removed envelope's baked values
sounding.

The fix is ``tree._invalidate_caches()``, not ``_post_mutation``: deleting a
pfield override is a data write, and ``_post_mutation`` would additionally
purge instrument bindings, which a pfield delete has no business doing.
"""

import warnings

from klotho.dynatos.envelopes import Envelope
from klotho.thetos import CompositionalUnit as UC


def _uc():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
            pfields={'amp': 0.1})
    return uc, list(uc._rt.leaf_nodes)


class TestRemovingAnEnvelopeRemovesItsSound:
    """The symptom a composer meets. They add a control envelope, hear it,
    remove it, and it keeps sounding."""

    def test_the_baked_values_go_when_the_envelope_goes(self):
        uc, leaves = _uc()
        env_id = uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp',
                                   node=leaves, control=True)
        with_envelope = list(uc.events['amp'])
        assert len(set(with_envelope)) > 1, 'fixture did not take'

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc.remove_envelope(env_id)

        assert list(uc.events['amp']) == [0.1, 0.1, 0.1, 0.1], (
            f'the removed envelope is still sounding: {list(uc.events["amp"])}'
        )

    def test_it_is_gone_from_LOWERING_too_not_only_from_inspection(self):
        """The half the docket row got wrong. ``uc.events`` and the snapshot
        that feeds playback are two different memos, and this defect reached
        both -- so it was never merely an inspection lie."""
        uc, leaves = _uc()
        env_id = uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp',
                                   node=leaves, control=True)
        uc.events                                   # prime both memos

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc.remove_envelope(env_id)

        snapshot = uc._build_effective_parameter_tree()
        values = [snapshot[n].get('amp') for n in snapshot.leaf_nodes]
        assert values == [0.1, 0.1, 0.1, 0.1], (
            f'the lowering snapshot still carries the removed envelope: '
            f'{values}'
        )


class TestABareFieldDeleteInvalidatesLikeAWrite:
    """The mechanism, one level down, so the next reader sees the rule rather
    than the symptom: a delete and a write must be equally visible."""

    def test_remove_fields_moves_the_structure_version(self):
        uc, leaves = _uc()
        uc.set_pfields(leaves[1], amp=0.7)
        version = uc._rt._structure_version

        uc._rt.remove_fields(leaves[1], ['amp'])

        assert uc._rt._structure_version != version, (
            'a field delete left the structure version where it was, so every '
            'consumer memoized on it serves the deleted value'
        )

    def test_a_primed_read_sees_the_delete(self):
        uc, leaves = _uc()
        uc.set_pfields(leaves[1], amp=0.7)
        assert list(uc.events['amp']) == [0.1, 0.7, 0.1, 0.1]

        uc._rt.remove_fields(leaves[1], ['amp'])

        assert list(uc.events['amp']) == [0.1, 0.1, 0.1, 0.1]

    def test_a_write_and_a_delete_are_equally_visible(self):
        """Stated as a symmetry, because the defect was an asymmetry: one of
        these two paths announced and the other did not."""
        uc, leaves = _uc()
        uc.events

        uc.set_pfields(leaves[2], amp=0.5)
        after_write = list(uc.events['amp'])
        uc._rt.remove_fields(leaves[2], ['amp'])
        after_delete = list(uc.events['amp'])

        assert after_write == [0.1, 0.1, 0.5, 0.1]
        assert after_delete == [0.1, 0.1, 0.1, 0.1]

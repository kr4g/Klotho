"""
Chunk 4 regression test: ``Envelope.at_time`` must not leak envelope
instances across the interpreter lifetime.

Before the fix, ``at_time`` used a module-level ``@lru_cache``, which keys
on ``self`` and therefore held a strong reference to every envelope ever
passed through it. With the per-instance dict cache, each envelope's cache
is freed when the envelope itself becomes unreachable.
"""

import gc
import weakref

from klotho.dynatos import Envelope


def test_envelopes_are_garbage_collected_after_at_time():
    refs = []
    for _ in range(200):
        env = Envelope([0.0, 1.0, 0.0], times=[0.5, 0.5])
        env.at_time(0.25)
        env.at_time(0.5)
        env.at_time(0.75)
        refs.append(weakref.ref(env))
        del env

    gc.collect()
    alive = sum(1 for r in refs if r() is not None)
    assert alive == 0, (
        f"After GC, {alive} of {len(refs)} envelopes are still alive. "
        "Pre-fix @lru_cache leaked all of them."
    )


def test_at_time_cache_is_instance_scoped():
    env_a = Envelope([0.0, 1.0], times=[1.0])
    env_b = Envelope([0.0, 0.5], times=[1.0])

    va = env_a.at_time(0.5)
    vb = env_b.at_time(0.5)

    assert va == 0.5
    assert vb == 0.25

    assert 0.5 in env_a._at_time_cache
    assert 0.5 in env_b._at_time_cache
    assert env_a._at_time_cache is not env_b._at_time_cache


def test_repeated_at_time_hits_cache():
    env = Envelope([0.0, 1.0, 0.0], times=[0.5, 0.5])
    env.at_time(0.3)
    assert 0.3 in env._at_time_cache
    before_len = len(env._at_time_cache)
    for _ in range(10):
        env.at_time(0.3)
    assert len(env._at_time_cache) == before_len


def test_ordered_leaf_subset_preserves_insertion_order():
    """Chunk 4 #16: leaf_subset tuples preserve caller order for downstream
    iteration determinism."""
    from klotho.thetos import CompositionalUnit as UC
    from klotho.thetos.instruments.synthdef import SynthDefInstrument

    inst = SynthDefInstrument(
        name='tri', defName='kl_tri',
        pfields={'amp': 0.1, 'freq': 440.0}
    )
    uc = UC(
        tempus='4/4', prolatio=(1, 1, 1, 1, 1, 1),
        beat='1/4', bpm=60, inst=inst, pfields=['amp']
    )
    leaves = list(uc.rt.leaf_nodes)
    subset = [leaves[2], leaves[3], leaves[4]]
    env = Envelope([0.0, 1.0], times=[1.0])
    uc.apply_envelope(envelope=env, pfields='amp', node=subset, control=True)
    desc = next(iter(uc._control_envelopes.values()))
    assert desc["leaf_subset"] is not None
    assert isinstance(desc["leaf_subset"], tuple)
    assert list(desc["leaf_subset"]) == subset

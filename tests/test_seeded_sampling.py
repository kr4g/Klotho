"""Seeded drawing from a pool (charter WL-12, NEW-25).

WL-12's premise needed one correction: ``Pattern.from_random`` was already
reproducible, through ``np.random.seed`` -- the global numpy stream. What was
missing is a per-call seed, so reproducibility did not require mutating
process-global state. The ``seed=None`` path is deliberately left drawing from
that global stream, so anyone relying on ``np.random.seed`` keeps working.

Two RNG conventions survive here on purpose, and they split cleanly: stdlib
``random.Random`` for object-pool draws, numpy ``Generator`` for the
array-and-``p=`` numeric ones.
"""

import random

import numpy as np
import pytest

from klotho.topos.collections.sequences import Pattern
from klotho.utils.algorithms import sample_with_replacement
from klotho.utils.algorithms.random import diverse_sample


class TestSampleWithReplacement:
    def test_a_seed_reproduces_the_draw(self):
        assert sample_with_replacement(list('ABC'), 8, seed=42) == \
               sample_with_replacement(list('ABC'), 8, seed=42)

    def test_different_seeds_differ(self):
        assert sample_with_replacement(list('ABCDEFGH'), 12, seed=1) != \
               sample_with_replacement(list('ABCDEFGH'), 12, seed=2)

    def test_it_draws_with_replacement(self):
        drawn = sample_with_replacement([1, 2], 20, seed=0)
        assert len(drawn) == 20

    def test_every_draw_comes_from_the_pool(self):
        pool = [10, 20, 30]
        assert set(sample_with_replacement(pool, 30, seed=3)) <= set(pool)

    def test_weights_bias_the_draw(self):
        drawn = sample_with_replacement(list('ABC'), 200, seed=1,
                                        weights=[10, 1, 1])
        assert drawn.count('A') > drawn.count('B') + drawn.count('C')

    def test_a_zero_weight_is_never_drawn(self):
        assert 'C' not in sample_with_replacement(list('ABC'), 100, seed=1,
                                                  weights=[1, 1, 0])

    def test_arbitrary_objects_survive_intact(self):
        """The reason this is stdlib and not numpy: np.random.choice would
        coerce these into an object array and mangle them."""
        pool = [(1, 2), (3, 4)]
        for item in sample_with_replacement(pool, 6, seed=0):
            assert item in pool
            assert isinstance(item, tuple) and len(item) == 2

    def test_it_leaves_the_global_random_stream_alone(self):
        random.seed(1234)
        expected = [random.random() for _ in range(3)]
        random.seed(1234)
        sample_with_replacement(list('ABC'), 5, seed=7)
        assert [random.random() for _ in range(3)] == expected

    def test_a_random_random_instance_is_accepted(self):
        assert sample_with_replacement(list('ABC'), 5, seed=random.Random(11)) == \
               sample_with_replacement(list('ABC'), 5, seed=random.Random(11))

    def test_zero_draws_is_empty(self):
        assert sample_with_replacement([1, 2], 0) == []

    @pytest.mark.parametrize("args,kwargs,match", [
        (([1, 2], -1), {}, "non-negative"),
        (([], 2), {}, "non-empty"),
        (([1, 2], 2), {'weights': [1]}, "match"),
        (([1, 2], 2), {'weights': [-1, 1]}, "non-negative"),
        (([1, 2], 2), {'weights': [0, 0]}, "positive"),
    ])
    def test_bad_input_raises(self, args, kwargs, match):
        with pytest.raises(ValueError, match=match):
            sample_with_replacement(*args, **kwargs)

    def test_it_is_exported(self):
        import klotho.utils.algorithms as algs
        assert 'sample_with_replacement' in algs.__all__


class TestPatternFromRandom:
    ELEMENTS = list('ABCDEF')

    def test_a_seed_reproduces_the_structure(self):
        assert str(Pattern.from_random(self.ELEMENTS, length=6, seed=99)) == \
               str(Pattern.from_random(self.ELEMENTS, length=6, seed=99))

    def test_different_seeds_differ(self):
        assert str(Pattern.from_random(self.ELEMENTS, length=8, seed=1)) != \
               str(Pattern.from_random(self.ELEMENTS, length=8, seed=2))

    def test_the_unseeded_path_still_honours_np_random_seed(self):
        """Left deliberately on the global numpy stream; changing it would
        silently break anyone already seeding this way."""
        np.random.seed(7)
        first = str(Pattern.from_random(self.ELEMENTS, length=6))
        np.random.seed(7)
        assert str(Pattern.from_random(self.ELEMENTS, length=6)) == first

    def test_a_generator_is_accepted(self):
        assert str(Pattern.from_random(self.ELEMENTS, length=6,
                                       seed=np.random.default_rng(5))) == \
               str(Pattern.from_random(self.ELEMENTS, length=6,
                                       seed=np.random.default_rng(5)))

    def test_weights_still_validate(self):
        with pytest.raises(ValueError, match="match"):
            Pattern.from_random(self.ELEMENTS, length=4, weights=[1, 2], seed=1)

    def test_a_seeded_pattern_iterates_normally(self):
        pattern = Pattern.from_random(self.ELEMENTS, length=5, seed=3)
        assert len([next(pattern) for _ in range(pattern.length)]) == pattern.length

    def test_nesting_can_be_switched_off_reproducibly(self):
        flat = Pattern.from_random(self.ELEMENTS, length=6,
                                   nesting_probability=0.0, seed=4)
        assert all(item in self.ELEMENTS for item in flat.pattern)


class TestDiverseSampleOptionalDependency:
    """NEW-25. The packaging half was already solved -- diversipy is declared
    as the 'sampling' extra, not a hard dependency. What was wrong is that
    nothing said so at the point of failure."""

    def test_importing_the_package_never_needed_diversipy(self):
        import klotho.utils.algorithms as algs
        assert 'diverse_sample' in dir(algs)

    def test_the_error_names_the_extra(self):
        try:
            import diversipy  # noqa: F401
        except ImportError:
            with pytest.raises(ImportError, match="sampling"):
                diverse_sample(list('ABCDEF'), 2, 2)
        else:
            pytest.skip("diversipy is installed; the error path cannot run")

    def test_the_error_says_nothing_else_needs_it(self):
        try:
            import diversipy  # noqa: F401
        except ImportError:
            with pytest.raises(ImportError, match="Nothing else in Klotho"):
                diverse_sample(list('ABCDEF'), 2, 2)
        else:
            pytest.skip("diversipy is installed; the error path cannot run")

    def test_it_takes_a_seed_now(self):
        import inspect
        assert 'seed' in inspect.signature(diverse_sample).parameters

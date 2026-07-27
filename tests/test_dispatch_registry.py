"""TypeRegistry semantics + golden routing of the plot/convert registries."""
import pytest

from klotho.utils.dispatch_registry import TypeRegistry


class Base:
    pass


class Child(Base):
    pass


class GrandChild(Child):
    pass


class TestTypeRegistry:
    def test_exact_type_dispatch(self):
        reg = TypeRegistry('testing')
        reg.register(Base)(lambda o: 'base')
        assert reg.dispatch(Base()) == 'base'

    def test_subclass_inherits_base_handler(self):
        reg = TypeRegistry('testing')
        reg.register(Base)(lambda o: 'base')
        assert reg.dispatch(GrandChild()) == 'base'

    def test_subclass_handler_wins_regardless_of_registration_order(self):
        reg = TypeRegistry('testing')
        reg.register(Base)(lambda o: 'base')       # base registered FIRST
        reg.register(Child)(lambda o: 'child')
        assert reg.dispatch(Child()) == 'child'
        assert reg.dispatch(GrandChild()) == 'child'
        assert reg.dispatch(Base()) == 'base'

    def test_predicate_fallback_after_mro_miss(self):
        reg = TypeRegistry('testing')
        reg.register(Base)(lambda o: 'base')
        reg.register_predicate(lambda o: hasattr(o, 'quack'))(lambda o: 'duck')

        class Duck:
            quack = True

        assert reg.dispatch(Duck()) == 'duck'
        # registered type is preferred over a matching predicate
        class QuackingBase(Base):
            quack = True
        assert reg.dispatch(QuackingBase()) == 'base'

    def test_unsupported_raises_with_name(self):
        reg = TypeRegistry('plotting')
        with pytest.raises(TypeError, match='Unsupported object type for plotting'):
            reg.dispatch(object())

    def test_kwargs_forwarded(self):
        reg = TypeRegistry('testing')
        reg.register(Base)(lambda o, **kw: kw)
        assert reg.dispatch(Base(), a=1, b='x') == {'a': 1, 'b': 'x'}


class TestPlotRegistryRouting:
    """Golden: every supported type routes to the same handler as the old
    match statement."""

    def _route(self, obj):
        from klotho.semeios.visualization.plots import _PLOT_REGISTRY
        handler = _PLOT_REGISTRY.lookup(obj)
        assert handler is not None, f"no plot handler for {type(obj)}"
        return handler.__name__

    def test_tree_family(self):
        from klotho.topos.graphs import Tree
        from klotho.chronos.rhythm_trees import RhythmTree
        assert self._route(RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))) \
            == '_dispatch_rhythm_tree'
        assert self._route(Tree(1, (1, 1))) == '_dispatch_tree'

    def test_lattice_family(self):
        from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice
        assert self._route(ToneLattice(2, resolution=2)) == '_dispatch_lattice'

    def test_cps_before_cs(self):
        from klotho.tonos.systems.combination_product_sets import (
            CombinationProductSet, MasterSet,
        )
        assert self._route(CombinationProductSet.hexany()) == '_dispatch_cps'
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        assert self._route(ms) == '_dispatch_master_set'

    def test_tonal_types(self):
        from klotho.tonos import Scale, Chord, Voicing
        assert self._route(Scale(['1/1', '9/8', '5/4'])) == '_dispatch_scale_chord'
        assert self._route(Chord(['1/1', '5/4', '3/2'])) == '_dispatch_scale_chord'
        assert self._route(Voicing(['1/1', '3/2'])) == '_dispatch_scale_chord'

    def test_temporal_types(self):
        from klotho.chronos.temporal_units.temporal import (
            TemporalUnit, TemporalUnitSequence, TemporalBlock,
        )
        from klotho.thetos.composition.compositional import CompositionalUnit
        u = TemporalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        assert self._route(u) == '_dispatch_temporal_unit'
        assert self._route(uc) == '_dispatch_temporal_unit'  # via MRO
        assert self._route(TemporalUnitSequence([u])) == '_dispatch_timeline'
        assert self._route(TemporalBlock([u])) == '_dispatch_timeline'

    def test_unsupported_message_preserved(self):
        from klotho import plot
        with pytest.raises(TypeError, match='Unsupported object type for plotting'):
            plot(42)


class TestConvertRegistryRouting:
    """The playback converter dispatch keeps its exact per-type wiring."""

    def _handlers_recorder(self):
        calls = []

        class Recorder(dict):
            def __missing__(self, key):
                def h(obj, **kw):
                    calls.append((key, kw))
                    return key
                return h

        return Recorder(), calls

    def test_uc_routes_before_temporal_unit(self):
        from klotho.utils.playback._converter_base import dispatch_convert
        from klotho.thetos.composition.compositional import CompositionalUnit
        handlers, calls = self._handlers_recorder()
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        assert dispatch_convert(uc, {}, handlers) == 'compositional_unit'

    def test_chord_before_pitch_collection(self):
        from klotho.utils.playback._converter_base import dispatch_convert
        from klotho.tonos import Chord, Scale
        handlers, calls = self._handlers_recorder()
        assert dispatch_convert(Chord(['1/1', '5/4', '3/2']), {}, handlers) == 'chord'
        assert dispatch_convert(Scale(['1/1', '9/8']), {}, handlers) == 'scale'

    def test_chord_sequence_pause_default(self):
        from klotho.utils.playback._converter_base import dispatch_convert
        from klotho.tonos import Chord, ChordSequence
        handlers, calls = self._handlers_recorder()
        dispatch_convert(ChordSequence([Chord(['1/1', '3/2'])]), {}, handlers)
        key, kw = calls[-1]
        assert key == 'chord_sequence'
        assert kw['pause'] == 0.25

    def test_unsupported_type_raises(self):
        from klotho.utils.playback._converter_base import dispatch_convert
        with pytest.raises(TypeError, match='Unsupported object type'):
            dispatch_convert(object(), {}, {})

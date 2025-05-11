from klotho.topos.graphs.networks import ComboNet
from .cps import CombinationProductSet

class CombinationProductNetwork(ComboNet):
    def __init__(self, cps: CombinationProductSet):
        if not isinstance(cps, CombinationProductSet):
            raise ValueError("CombinationProductNetwork requires an instance of CombinationProductSet or its subclasses.")
        
        self._cps = cps
        
        nodes = {combo: {'product': cps.combo_to_product[combo], 'ratio': cps.combo_to_ratio[combo]} 
                 for combo in cps.combos}
        
        super().__init__(nodes=nodes)
        
        self._make_network()

    def _make_network(self):
        for combo1 in self._cps.combos:
            for combo2 in self._cps.combos:
                if combo1 != combo2:
                    common_factors = len(set(combo1) & set(combo2))
                    if common_factors > 0:
                        interval_forward = self._calculate_interval(combo1, combo2)
                        self.add_edge(combo1, combo2, common_factors=common_factors, interval=interval_forward)
                        
                        interval_reverse = self._calculate_interval(combo2, combo1)
                        self.add_edge(combo2, combo1, common_factors=common_factors, interval=interval_reverse)

    def _calculate_interval(self, source_combo, target_combo):
        source_ratio = self._cps.combo_to_ratio[source_combo]
        target_ratio = self._cps.combo_to_ratio[target_combo]
        return target_ratio / source_ratio

    def edge_interval(self, source, target):
        return self.edge_attributes(source, target).get('interval', None)
